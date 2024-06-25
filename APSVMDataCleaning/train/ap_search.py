import pickle, time, argparse, json
import lgdo
import multiprocessing as mp
import numpy as np
from sklearn.cluster import AffinityPropagation
from sklearn.metrics import pairwise_distances

'''
Use this script to find the optimal hyperparameters for AP.
'''

argparser = argparse.ArgumentParser()
argparser.add_argument("--file", help="file containing training data", type=str, required=True)
argparser.add_argument("--exemplars", help="number of clusters desired", type=int, required=True)
argparser.add_argument("--prefs", help="number of preference values", type=int)
argparser.add_argument("--damps", help="number of damping values", type=int)
args = argparser.parse_args()


# Load dsp table

sto = lgdo.lh5.LH5Store()
tb_dsp, _ = sto.read('ml_train/dsp', args.file)
wfs_norm = tb_dsp['wf_norm']['values']


#Precompute similarity matrix 

print("Computing similarity matrix")
start_time = time.time()
similarities = -pairwise_distances(wfs_norm, metric='l1', n_jobs=-1)
print("--- %s minutes elapsed for similarities---" % ((time.time() - start_time)/60))

median = np.median(similarities)
minimum = np.amin(similarities)

print(f"Median = {median}")
print(f"Minimum = {minimum}")

# Create search grid and define optimization function

if args.prefs: 
    n_prefs = args.prefs
else:
    n_prefs = 5

if args.damps: 
    n_damps = args.prefs
else: 
    n_damps = 5


maximum = -100 if median < -100 else median

preferences = np.linspace(minimum, maximum, n_prefs)
dampings = np.linspace(0.80, 0.99, n_damps)

grid = [(x,y) for x in preferences for y in dampings]

    
def ap_search(pref, damp, verbose=True):  
    
    ap = AffinityPropagation(max_iter=500,
                             convergence_iter=25, 
                             verbose=verbose,
                             random_state=0,
                             preference = pref,
                             damping= damp,
                             affinity='precomputed').fit(X=similarities)
    
    n_exemps = len(ap.cluster_centers_indices_)

    
    if verbose == True:
        print("--- %s minutes elapsed for AP iteration---" % ((time.time() - start_time)/60))
        print(f"Preference = {pref}, Damping = {damp}, Exemplars = {n_exemps}")
    
    return n_exemps

# Run global optimization 

n_cores = n_prefs*n_damps

print("Cores estimated = ", n_cores)


if n_cores > mp.cpu_count():
    n_cores = mp.cpu_count()
    
print("Cores available = ", n_cores)
    
start_time = time.time()
with mp.Pool(processes = n_cores) as p:
        result = np.array(p.starmap(ap_search, grid))
print("--- Elapsed time: %s minutes ---" % ((time.time() - start_time)/60))

# Get optimal results

if args.exemplars:
    target_exemps = args.exemplars
else:
    target_exemps = 100
diffs = abs(result - target_exemps)
opt_hyperpars, opt_result = grid[np.argmin(diffs)], result[np.argmin(diffs)]

print("Preference = ", opt_hyperpars[0])
print("Damping = ", opt_hyperpars[1])
print("Exemplars = ", opt_result)

# Train optimal AP

start_time = time.time()
ap_opt = AffinityPropagation(max_iter=500,
                         convergence_iter=25, 
                         verbose=True,
                         random_state=0,
                         preference = opt_hyperpars[0],
                         damping= opt_hyperpars[1],
                         affinity='precomputed').fit(X=similarities)
print("--- Elapsed time: %s minutes ---" % ((time.time() - start_time)/60))
n_exemps_opt = len(ap_opt.cluster_centers_indices_)

# Save hyperparameters and model

with open('../data/hyperparameters.json', 'rb') as infile:
    hyperparams_dict = json.load(infile)
    
hyperparams_dict['AP']['median'] = str(median)
hyperparams_dict['AP']['minimum'] = str(minimum)
hyperparams_dict['AP']['damping'] = str(opt_hyperpars[1])
hyperparams_dict['AP']['preference'] = str(opt_hyperpars[0])
hyperparams_dict['AP']['exemplars'] = str(n_exemps_opt)

infile.close()

with open("../data/hyperparameters.json", "w") as outfile:
    json.dump(hyperparams_dict, outfile, indent=3)
    
outfile.close()
    
with open("../data/ap.pkl", "wb") as ap_file:
    pickle.dump(ap_opt, ap_file, protocol=pickle.HIGHEST_PROTOCOL)
    
ap_file.close()
    
print("Hyperparameters and model saved")