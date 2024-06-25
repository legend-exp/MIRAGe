import time, pickle, json, argparse
import numpy as np
import lgdo
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import loguniform

'''
Use this script to find the optimal hyperparameters for a SVM.
'''

argparser = argparse.ArgumentParser()
argparser.add_argument("--file", help="file containing training data", type=str, required=True)
args = argparser.parse_args()

# Load files

sto = lgdo.lh5.LH5Store()
tb_dsp, _ = sto.read('ml_train/dsp', args.file)
    
with open('../data/hyperparameters.json', 'r') as infile:
    hyperparams_dict = json.load(infile)

# Define training inputs

dwts_norm = tb_dsp['dwt_norm'].nda
labels = tb_dsp['dc_label'].nda
SVM_hyperparams = hyperparams_dict['SVM']


# Initialize optimization

print("Initializing optimization grid")

C_dist = loguniform(1e-2, 1e10)
gamma_dist = loguniform(1e-9, 1e3)
param_dist = dict(gamma=gamma_dist, C=C_dist)

cv = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=0)

clf = SVC(random_state=SVM_hyperparams['random_state'], 
          kernel=SVM_hyperparams['kernel'], 
          decision_function_shape =SVM_hyperparams['decision_function_shape'], 
          class_weight=SVM_hyperparams['class_weight'])

grid = RandomizedSearchCV(estimator=clf,
                          param_distributions=param_dist, 
                          cv=cv,
                          n_iter=100,
                          verbose=2,
                          n_jobs=-1 
                         )
# Close input file 

infile.close()

# Run optimizations

print("Starting random hyperparameter search")
start_time = time.time()
grid.fit(dwts_norm, labels)
print("--- %s minutes elapsed ---" % ((time.time() - start_time)/60))

print(
    "The best parameters for the SVM are %s with a score of %0.2f"
    % (grid.best_params_, grid.best_score_)
)

hyperparams_dict['SVM']['C'] = str(grid.best_params_['C'])
hyperparams_dict['SVM']['gamma'] = str(grid.best_params_['gamma'])
hyperparams_dict['SVM']['score'] = str(grid.best_score_)

with open("../data/hyperparameters.json", "w") as outfile:
    json.dump(hyperparams_dict, outfile, indent=3)
    
# Close output file 

outfile.close()
    
print("Hyperparameters saved")