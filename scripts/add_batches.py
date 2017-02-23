from os import listdir
from os.path import isfile, join
import pandas as pd
import ConfigParser
turkpath = '../turkApi/'
batchpath = turkpath+'batch/'
configpath = turkpath+'config/'
onlyfiles = [f for f in listdir(batchpath) if isfile(join(batchpath, f))]
for batch in onlyfiles:
    ts = batch.split('.')[-2]
    metadata = pd.read_csv(join(batchpath, batch), sep='\t')
    desc_string = batch.split('.config')[0]
    config_file_name = desc_string+'.config'
    config = ConfigParser.ConfigParser()
    config.read(join(configpath, config_file_name))
    mturk_params = {x:y for x, y in config.items('default')}
    print "INSERT Batch"
    print ts, desc_string, {}, mturk_params
    break

