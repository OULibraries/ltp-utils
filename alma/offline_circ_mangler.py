##  Timestamp mangler for Alma offline circ.
##  Useful for reloading failed offline circ transactions.
##  Sets Alma offline circ date to yesterday, but leaves the hours:minutes the same
##  Will crawl specified directory recursively.
##  Two output directories:
##      One is a "return all" directory for checking everything back in.
##      The other is a "reloan" directory for reloaning materials.
##      Original data is left untouched.

import os
import re
import datetime
from time import strftime

# Change timestamp for transaction yesterday
yesterday = datetime.date.today () - datetime.timedelta (days=1)
yesterday = yesterday.strftime("%Y%m%d") 
#today = strftime("%Y%m%d")
#now = strftime("%Y%m%d%H%M")

## Regex match for any transaction
prev_trans = re.compile('^((\d{4})(\d{2})(\d{2})(\d{2})(\d{2}))(L|R)([^\s]+)(\s+)(.*)$')
## Regex match for loan transaction
prev_loan = re.compile('^((\d{4})(\d{2})(\d{2})(\d{2})(\d{2}))(L)([^\s]+)(\s+)(.*)$')
## Regex match for return transaction
prev_return = re.compile('^((\d{4})(\d{2})(\d{2})(\d{2})(\d{2}))(R)([^\s]+)(\s+)(.*)$')
 
# The top argument for walk
indir  = 'C:/Alma Offline Circulation/OffCirc/files/'
outdir = indir.rstrip('\\')
outdir = outdir.rstrip('/')
returnall_dir = outdir + '_returnall\\'
reloan_dir = outdir + '_reloan\\'
# The extension to search for
exten = '.dat'
for inpath, dirnames, files in os.walk(indir):
    for name in files:
        if name.lower().endswith(exten):
            ## Set the full path for input files
            inputname = os.path.join(inpath, name)
            ## Set the full path for returning all items
            returnall_path = inpath.replace(indir, returnall_dir)
            returnall_name = os.path.join(returnall_path, name)
            ## Set the full path for reloaning items
            reloan_path = inpath.replace(indir, reloan_dir)
            reloan_name = os.path.join(reloan_path, name)
            ## Create any required directories
            if not os.path.exists(os.path.dirname(returnall_name)):
                os.makedirs(os.path.dirname(returnall_name))
            if not os.path.exists(os.path.dirname(reloan_name)):
                os.makedirs(os.path.dirname(reloan_name))
            ## Open file handles
            input = open(inputname, 'r')
            returnall = open(returnall_name, 'w')
            reloan = open(reloan_name, 'w')
            ## Skip empty lines on input
            for input_line in input:
                if not input_line.strip():
                    continue
                else:
                    ## Update timestamp and set all transactions to return for returnall folder
                    returnall_line = prev_trans.sub(yesterday+r'\5\6R\8\9', input_line )
                    ## Write returns with the new timestamps to returnall folder
                    returnall.write(returnall_line)
                    ## Update loans with the new timestamps for reloan folder
                    reloan_line = prev_loan.sub(yesterday+r'\5\6L\8\9\10', input_line )
                    ## Strip out returns for reloan folder
                    reloan_line = prev_return.sub(r'', reloan_line )
                    ## Skip empty lines created by stripping out returns
                    if not reloan_line.strip():
                        continue
                    else:
                        ## Write loans with the new timestamps to reloan folder
                        reloan.write(reloan_line)
            ## Close filehandles
            input.close()
            returnall.close()
            reloan.close()
