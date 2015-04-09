import argparse
import os
import sys
import codecs
import bagit
import hashlib
import time
import boto
from boto.exception import JSONResponseError
import boto.dynamodb2
from boto.dynamodb2.exceptions import ItemNotFound, ConditionalCheckFailedException
from boto.dynamodb2.fields import HashKey, RangeKey, KeysOnlyIndex, GlobalAllIndex
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import NUMBER
import boto.glacier
from boto.glacier.exceptions import UnexpectedHTTPResponseError

## Get CLI arguments
parser = argparse.ArgumentParser(description="Backup and restore LC Bags to/from Amazon Glacier")
group = parser.add_mutually_exclusive_group()
group.add_argument("-f", "--freeze", action="store_true", help="backup to Amazon Glacier")
group.add_argument("-t", "--thaw", action="store_true", help="restore from Amazon Glacier")
group.add_argument("-s", "--setup", action="store_true", help="Get AWS Setup information")
parser.add_argument("-vid", "--vaultid", help="the name of the Amazon Glacier Vault")
parser.add_argument("-b", "--bag", help="the name of the bag")
parser.add_argument("-p", "--path", help="the parent directory of the bag")
args = parser.parse_args()
## TODO validate + freeze, then upgrade bag, + freeze changes
if args.setup:
    print('''
You'll need to have aws credentials on the computer running this script.
    see:
    https://boto.readthedocs.org/en/latest/boto_config_tut.html

You'll also need to create IAM policies to allow this user to deal with
DynamoDB and Glacier.
    see:
    https://docs.aws.amazon.com/IAM/latest/UserGuide/PoliciesOverview.html

Below is an example policy:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:BatchGetItem",
                "dynamodb:BatchWriteItem",
                "dynamodb:CreateTable",
                "dynamodb:DeleteItem",
                "dynamodb:DescribeTable",
                "dynamodb:GetItem",
                "dynamodb:ListTables",
                "dynamodb:PutItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:UpdateItem",
                "dynamodb:UpdateTable"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:*:table/freezerbag_*"
            ]
        }
    ],
    "Statement": [
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:glacier:us-east-1:*:vaults/*",
                "arn:aws:glacier:us-east-2:*:vaults/*",
                "arn:aws:glacier:us-west-1:*:vaults/*",
                "arn:aws:glacier:us-west-2:*:vaults/*"
            ],
            "Action": [
                "glacier:DescribeVault",
                "glacier:UploadArchive",
                "glacier:InitiateMultipartUpload",
                "glacier:AbortMultipartUpload",
                "glacier:UploadMultipartPart",
                "glacier:UploadPart",
                "glacier:ListParts",
                "glacier:InitiateJob",
                "glacier:ListJobs",
                "glacier:GetJobOutput",
                "glacier:ListMultipartUploads",
                "glacier:CompleteMultipartUpload"
            ]
        },
        {
            "Effect": "Allow",
            "Resource": [
                "arn:aws:glacier:us-east-1:*",
                "arn:aws:glacier:us-east-2:*",
                "arn:aws:glacier:us-west-1:*",
                "arn:aws:glacier:us-west-2:*"
            ],
            "Action": [
                "glacier:ListVaults"
            ]
        }
    ]
}

Note that this policy is probably more open than what you would want to run in production.
You probably want to limit the account to writing to predetermined vaults.
    ''')
    exit()
    
## Set those variables to something useful
fulbagpath = os.path.normpath(os.path.abspath(os.path.join(args.path, args.bag)))
vault_name = args.vaultid


# We'll record stuff in amazon relative to the bag directory, rather than the
# absolute path
bagname = os.path.basename(fulbagpath)
bagparent = os.path.dirname(fulbagpath)
relbagpath = os.path.relpath(fulbagpath, bagparent)

## Our DynamoDB tables
archives = Table('freezerbag_archives')
hashes = Table('freezerbag_hashes')
names = Table('freezerbag_names')
jobs = Table('freezerbag_jobs')

## Set up translation table for character replacement in filenames
filetranstable = dict.fromkeys(map(ord, '\\'), u'/')


class GlacierVault:
    """
    Wrapper for uploading/download archive to/from Amazon Glacier Vault
    Makes use of DynamoDB to store archive id corresponding to filename and waiting jobs.

    Backup:
    >>> GlacierVault("myvault")upload("myfile")
    
    Restore:
    >>> GlacierVault("myvault")retrieve("myfile")

    or to wait until the job is ready:
    >>> GlacierVault("myvault")retrieve("serverhealth2.py", True)
    """
    def __init__(self, vault_name):
        """
        Initialize the vault
        """
        layer2 = boto.connect_glacier()
                                    
        self.vault = layer2.get_vault(vault_name)

        ## Bodge to fix Boto unicode bug
        ## see https://github.com/boto/boto/issues/2603
        self.vault.name = str(self.vault.name)

    def upload(self, filename, file_hash):
        """
        Upload filename and store the archive id for future retrieval
        """
        
        rel_filename = os.path.relpath(filename, bagparent)
        archive_id = self.vault.concurrent_create_archive_from_file(filename, description=rel_filename)
        
        # Storing the archive_id, filename, file_hash, and bag_date relationships in dynamodb
        try:
            archives.put_item(data={
                'archive_id': archive_id,
                'vault_name': vault_name,
                'file_hash': file_hash,
                'filename': rel_filename,
            })
        ## If the database doesn't exist, create it
        except JSONResponseError as e:
            if e.status == 400 and e.message == 'Requested resource not found':
                print('freezerbag_archives table missing, creating now')
                Table.create('freezerbag_archives', schema=[HashKey('archive_id'), RangeKey('vault_name', data_type='S')])
                time.sleep(30)
            ## Bail if we hit a JSON error we don't understand
            else:
                print(e.status)
                print(e.message)
                exit()
        ## Now try to write again, and die if it fails.  This is ugly, and should be done in a try loop or something.        
        try:
            hashes.put_item(data={
                'file_hash': file_hash,
                'archive_id': archive_id,
                'vault_name': vault_name,
            })
        except:
            raise
        try:
            names.put_item(data={
                'filename': rel_filename,
                'bag_date': bag_date,
                'bagname': bagname,
                'archive_id': archive_id,
                'file_hash': file_hash,
                'vault_name': vault_name,
            })
        ## If the database doesn't exist, create it            
        except JSONResponseError as e:
            if e.status == 400 and e.message == 'Requested resource not found':
                print('freezerbag_names table missing, creating now')
                print('freezerbag_names table missing, creating now')
                Table.create('freezerbag_names', schema=[HashKey('filename'), RangeKey('bag_date', data_type=NUMBER)])
                time.sleep(30)
            ## Bail if we hit a JSON error we don't understand
            else:
                print(e.status)
                print(e.message)
                exit()
                
    def get_archive_id(self, filename, bag_date):
        """
        Get the archive_id corresponding to the filename and this bag's date
        """
        try:
            name = names.get_item(filename=filename, bag_date=bag_date)
            return name['archive_id']
        ## If the database doesn't exist, create it
        except JSONResponseError as e:
            if e.status == 400 and e.message == 'Requested resource not found':
                print('freezerbag_names table missing, creating now')
                Table.create('freezerbag_names', schema=[HashKey('filename'), RangeKey('bag_date', data_type=NUMBER)])
                time.sleep(30)
                return None
            ## Bail if we hit a JSON error we don't understand
            else:
                print(e.status)
                print(e.message)
                exit()
        except ItemNotFound:
            return None
            
    def get_hashes_archive_id(self, file_hash):
        """
        Get the archive_id corresponding to the file_hash
        """
        
        try:
            hash = hashes.get_item(file_hash=file_hash)
            return hash['archive_id']
        ## If the database doesn't exist, create it
        except JSONResponseError as e:
            if e.status == 400 and e.message == 'Requested resource not found':
                print('freezerbag_hashes table missing, creating now')
                Table.create('freezerbag_hashes', schema=[HashKey('file_hash')])
                ## Leave some time for the table to get created
                time.sleep(30)
                return None
            ## Bail if we hit a JSON error we don't understand
            else:
                print(e.status)
                print(e.message)
                exit()
        except ItemNotFound:
            return None
            
    def get_hashes_filename(self, file_hash):
        """
        Get the filename corresponding to the file_hash
        """
        
        try:
            hash = hashes.get_item(file_hash=file_hash)
            archive_id = hash['archive_id']
            archive = archives.get_item(archive_id=archive_id, vault_name=vault_name)
            return archive['filename']
        ## If the database doesn't exist, create it
        except JSONResponseError as e:
            if e.status == 400 and e.message == 'Requested resource not found':
                print('freezerbag_hashes table missing, creating now')
                Table.create('freezerbag_hashes', schema=[HashKey('file_hash'), RangeKey('bag_date', data_type=NUMBER)])
                time.sleep(30)
                return None
            ## Bail if we hit a JSON error we don't understand
            else:
                print(e.status)
                print(e.message)
                exit()
        except ItemNotFound:
            return None

            
            
    def retrieve(self, archive_id, filename, bag_date, wait_mode=False):
        """
        Initiate a Job, check its status, and download the archive when it's completed.
        """
        filename = os.path.normpath(filename.translate(filetranstable))
        bag_date = str(bag_date)
        #archive_id = self.get_archive_id(filename, bag_date)
        destdir = os.path.normpath(os.path.abspath(os.path.join(bagparent, bag_date)))
        destfile = os.path.normpath(os.path.abspath(os.path.join(destdir, filename)))
        archive_id = str(archive_id)
        if not archive_id:
            return
        # We'll use this to reference the retrieval job, whether it already exists or if we're firing it up.
        job = None
        
        # Is the job in the db?
        try:
            jobcheck = jobs.get_item(archive_id=archive_id, vault_name=vault_name)
            job_id = str(jobcheck['job_id'])
            ## If so, try to get the job from glacier
            try:
                job = self.vault.get_job(job_id)
            ## TODO we probably need to clean the job from the table in this case.
            except UnexpectedHTTPResponseError: # Return a 404 if the job is no longer available
                pass
        ## If the database doesn't exist, create it then initialize the job
        except JSONResponseError as e:
            if e.status == 400 and e.message == 'Requested resource not found':
                print('freezerbag_jobs table missing, creating now')
                Table.create('freezerbag_jobs', schema=[HashKey('archive_id', data_type='S'), RangeKey('vault_name', data_type='S')])
                time.sleep(30)
                # Job initialization
                job = self.vault.retrieve_archive(archive_id)
                # Note it in the db
                job_id = job.id
                jobs.put_item(data={
                    'archive_id': archive_id,
                    'job_id': job_id,
                    'vault_name': vault_name,
                    'filename': filename,
                })
            ## Bail if we hit a JSON error we don't understand
            else:
                print(e.status)
                print(e.message)
                exit()
        ## If the db exists, but the job isn't in the db, initialize it
        except ItemNotFound:
            # Job initialization
            job = self.vault.retrieve_archive(archive_id)
            # Note it in the db
            job_id = job.id
            print(job_id)
            jobs.put_item(data={
                'archive_id': archive_id,
                'job_id': job_id,
                'vault_name': vault_name,
                'filename': filename,
            })

        print(("Job {action}: {status_code} ({creation_date}/{completion_date})".format(**job.__dict__)))

        # checking manually if job is completed every 10 seconds instead of using Amazon SNS
        if wait_mode:
            while 1:
                job = self.vault.get_job(job_id)
                if not job.completed:
                    time.sleep(10)
                else:
                    break

        if job.completed:
            print("Downloading to %s" % (destfile))
            if not os.path.exists(os.path.dirname(destfile)):
                os.makedirs(os.path.dirname(destfile))
            ## verify_hashes=False is do to a boto bug in 2.36.0 + python3.x.
            # We're doing bag validation anyway, so this isn't a deal-breaker, though it hurts efficiency
            ## https://github.com/boto/boto/issues/3059
            job.download_to_file(destfile, verify_hashes=False)
        else:
            print("destfile: %s" % (destfile))

def hashfile(file, hasher, blocksize=65536):
    buf = file.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = file.read(blocksize)
    return hasher.hexdigest()

## Backup to glacier
if args.freeze:
    # Check if path exits
    if os.path.exists(fulbagpath):
        bag = bagit.Bag(fulbagpath)
    else:
        sys.exit("Bag \"%s\" not found!" % fulbagpath)

    if bag.is_valid():
        ## Upgrade 0.96 bags to 0.97 to get metadata validation. Skip this for now
        ## TODO validate + freeze, then upgrade bag, + freeze changes
        # if bag.version == "0.96":
            # txt = """BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"""
            # bagittxt = os.path.normpath(os.path.abspath(os.path.join(fulbagpath, "bagit.txt")))
            # with open(bagittxt, "w") as bagit_file:
                # bagit_file.write(txt)
            # bag.save()
            # # Reload the bag
            # bag = None
            # bag = bagit.Bag(fulbagpath)
            # # Revalidate the bag
            # if bag.is_valid():
                # print("Upgraded %s " % fulbagpath)
                # print("Bag is valid!")
        # else:
            print("Bag is valid!")
    else:
        sys.exit("Bag \"%s\" is invalid!" % fulbagpath)

    ## As of version 2.2, the LC Bagger program changed bagging-* to packing-* so we need to check for both
    if 'Bagging-Date' in bag.info:
        bag_date = int(bag.info['Bagging-Date'].replace('-', ''))
        tagfiles = ['bag-info.txt', 'bagit.txt', 'manifest-md5.txt', 'tagmanifest-md5.txt']
    if 'Packing-Date' in bag.info:
        bag_date = int(bag.info['Packing-Date'].replace('-', ''))
        tagfiles = ['package-info.txt', 'bagit.txt', 'manifest-md5.txt', 'tagmanifest-md5.txt']

    ## Create a dictionary for the tagfiles structured just like the bag item dict
    tagfiledict = {}
    for metadata in tagfiles:
        metadatafile = os.path.normpath(os.path.abspath(os.path.join(fulbagpath, metadata)))
        metadatahash = hashfile(open(metadatafile, 'rb'), hashlib.md5())
        tagfiledict[metadata] = {"md5":metadatahash}
        
    ## Combine the home-made tafiles and bag entries dicts
    combodict = {}
    for d in (tagfiledict, bag.entries):
        combodict.update(d)

    ## Upload bag
    for data, fixity in list(combodict.items()):
        # Create a normalized path for the file
        datafile = os.path.normpath(os.path.abspath(os.path.join(fulbagpath, data)))
        datahash = fixity["md5"]
        hashes_archive_id = GlacierVault(vault_name).get_hashes_archive_id(datahash)
        # See if we've already put it in glacier
        if hashes_archive_id:
            # If so, see if we need to add another filename entry
            # eg. the file is in the bag in two different places
            rel_filename = os.path.relpath(datafile, bagparent)
            hashes_filename = GlacierVault(vault_name).get_hashes_filename(datahash)
            try:
                name = names.get_item(filename=rel_filename, bag_date=bag_date)
                print("%s already in glacier." % hashes_filename)
                print("\tarchive_id: %s" % hashes_archive_id)
            except ItemNotFound:
                archive_id = hashes_archive_id
                file_hash = datahash
                print("archive_id: %s already in glacier\n\tas %s" % (archive_id, hashes_filename))
                print("\tadding %s as an additional filename" % rel_filename)
                ## This is duplicated code that should really be de-duped
                names.put_item(data={
                    'filename': rel_filename,
                    'bag_date': bag_date,
                    'bagname': bagname,
                    'archive_id': archive_id,
                    'file_hash': file_hash,
                    'vault_name': vault_name,
                })    
        else:
            GlacierVault(vault_name).upload(datafile, datahash)
            print("Uploaded \"%s\"" % datafile)
if args.thaw:
    ## Get all of the files with the listed bag name
    files = names.scan(
        bagname__eq=bagname,
    )
    
    ## Restore all versions of the bag.
    for file in files:
        vault_name = file['vault_name']
        archive_id = file['archive_id']
        filename = file['filename']
        bag_date = file['bag_date']
        GlacierVault(vault_name).retrieve(archive_id, filename, bag_date)
        
    ## Validated the restored bag. Need to store have bagname + bagdates to make this automated.
    ## Doing this manually for now.
    # destdir = os.path.normpath(os.path.abspath(os.path.join(bagparent, bag_date)))
    # destfile = os.path.normpath(os.path.abspath(os.path.join(destdir, filename)))
    # if os.path.exists(fulbagpath):
        # bag = bagit.Bag(fulbagpath)
    # else:
        # sys.exit("Bag \"%s\" not found!" % fulbagpath)
        
    # if bag.is_valid():
