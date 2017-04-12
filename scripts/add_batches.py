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
    if mturk_params['target'] == 'sandbox':
        continue
    if mturk_params['answer_field'] == 'entities':
        task_type = 'mention';
    if mturk_params['answer_field'] == 'relations':
        task_type = 'relation';
    if mturk_params['answer_field'] == 'links':
        task_type = 'link';
    batch_params = {'type': task_type}
    batch_desc =  
    print "INSERT Question Batch"
    print ts, , batch_params, mturk_params
    print "INSERT Mturk Batch"
    print ts, desc_string, batch_params, mturk_params
    print "INSERT Question"
    #Get from SQL
    batch_id = 0
    for _, row in metadata.iterrow():
        if batch_params['type'] == 'mention':
            question_params = {'doc_id': row['docId'].split('.json')[0]}
        if batch_params['type'] == 'relation':
            doc_string = row['docId'].split('.json')[0]
            doc_id, m1b, m1e, m2b, m2e = doc_string.split('-')
            question_params = {'doc_id': doc_id, 'm1_id': "{1}:{2}-{3}".format(doc_id, m1b, m1e), 'm2_id':"{1}:{2}-{3}".format(doc_id, m2b, m2e)}

        row['HITId'], row['HITTypeId'], 
    break

