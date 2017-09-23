import os
import subprocess
import sys
import random
import time
import tensorflow as tf
import itertools
from collections import OrderedDict

'''
This module simulates the gridsearch funtionality, in order to tune the hyperparmaters
'''

tf.flags.DEFINE_integer("seed", 0, "the global simulation seed for np and tf")
tf.flags.DEFINE_string("type", " ", "model type")

FLAGS = tf.flags.FLAGS

def gen_cmd(cfg_dict, seed):
    string = "python3 ./model.py"
    name = " --name="
    for key, val in cfg_dict.items():
        if key == 'grad_clip_val':
            string += " --"+str(key)+"_min="+str(val[0])
            string += " --"+str(key)+"_max="+str(val[1])
            name += str(key)+"#"+str(val[0])+"*"+str(val[1])+"~"
        else:
            string += " --"+str(key)+"="+str(val)
            if key == 'max_output_ops' or key == 'train_fn' or key == 'model': continue
            name += str(key)+"#"+str(val)+"~"
    if seed == 0: seed = int(round(random.random()*100000))
    name += "seed#" + str(seed)
    seed  = " --seed="+str(seed)
    return string + seed + name

#cfg to iterate over
'''
params=OrderedDict(
    state_size = [50, 100, 200],
    num_samples = [1500, 5000, 30000],
    batch_size  = [50, 100, 500],
    learning_rate = [0.01, 0.005],
    #learning_rate = [0.01, 0.005, 0.0005],
    grad_norm = [10e2],
    #grad_norm = [10e1, 10e2, 10e3],
    max_output_ops = [5],
    num_features = [3],
    train_fn = ["np_mult"],
    model = ["RNN"],
    norm = [True]
)
'''
#gridsearch for supervised models

if FLAGS.type == "RNN1":
    params=OrderedDict()
    params['total_num_epochs'] = [10000]
    params['state_size'] = [50, 50]
    params['test_ratio'] = [0.5]
    params['num_samples'] = [2]
    params['batch_size']  = [1]
    params['learning_rate'] = [0.01]
    params['epsilon'] = [1e-3]
    params['max_output_ops'] = [5]
    params['num_features'] = [4]    
    params['train_fn'] = ["np_add"]
    params['model'] = ["RNN"]
    params['norm'] = [True]
    params['clip'] = [False]
    params['state_fn'] = ["relu"]
    params['softmax_sat'] = [100]
    params['augument_grad'] = [True]
    params['add_noise'] = [True]
    params['hardmax_break'] = [False]

elif FLAGS.type == "RNN2":
    params=OrderedDict()
    params['total_num_epochs'] = [10000]
    params['state_size'] = [50, 50]
    params['test_ratio'] = [0.33]
    params['num_samples'] = [15]
    params['batch_size']  = [4]
    params['learning_rate'] = [0.01]
    params['epsilon'] = [1e-3]
    params['max_output_ops'] = [5]
    params['num_features'] = [4]    
    params['train_fn'] = ["np_add"]
    params['model'] = ["RNN"]
    params['norm'] = [True]
    params['clip'] = [False]
    params['state_fn'] = ["relu"]
    params['softmax_sat'] = [100]
    params['augument_grad'] = [True]
    params['add_noise'] = [True]
    params['hardmax_break'] = [False]

elif FLAGS.type == "RNN3":
    params=OrderedDict()
    params['total_num_epochs'] = [10000]
    params['state_size'] = [50, 50]
    params['test_ratio'] = [0.33]
    params['num_samples'] = [150]
    params['batch_size']  = [10]
    params['learning_rate'] = [0.01]
    params['epsilon'] = [1e-3]
    params['max_output_ops'] = [5]
    params['num_features'] = [4]    
    params['train_fn'] = ["np_add"]
    params['model'] = ["RNN"]
    params['norm'] = [True]
    params['clip'] = [False]
    params['state_fn'] = ["relu"]
    params['softmax_sat'] = [100]
    params['augument_grad'] = [True]
    params['add_noise'] = [True]
    params['hardmax_break'] = [False]

elif FLAGS.type == "RNN4":
    params=OrderedDict()
    params['total_num_epochs'] = [10000]
    params['state_size'] = [50, 50]
    params['test_ratio'] = [0.33]
    params['num_samples'] = [1500]
    params['batch_size']  = [100]
    params['learning_rate'] = [0.01]
    params['epsilon'] = [1e-3]
    params['max_output_ops'] = [5]
    params['num_features'] = [4]    
    params['train_fn'] = ["np_add"]
    params['model'] = ["RNN"]
    params['norm'] = [True]
    params['clip'] = [False]
    params['state_fn'] = ["relu"]
    params['softmax_sat'] = [100]
    params['augument_grad'] = [True]
    params['add_noise'] = [True]
    params['hardmax_break'] = [False]

elif FLAGS.type == "RNN5":
    params=OrderedDict()
    params['total_num_epochs'] = [10000]
    params['state_size'] = [50, 50]
    params['test_ratio'] = [0.33]
    params['num_samples'] = [3500]
    params['batch_size']  = [100]
    params['learning_rate'] = [0.01]
    params['epsilon'] = [1e-3]
    params['max_output_ops'] = [5]
    params['num_features'] = [4]    
    params['train_fn'] = ["np_add"]
    params['model'] = ["RNN"]
    params['norm'] = [True]
    params['clip'] = [False]
    params['state_fn'] = ["relu"]
    params['softmax_sat'] = [100]
    params['augument_grad'] = [True]
    params['add_noise'] = [True]
    params['hardmax_break'] = [False]

elif FLAGS.type == "RL":
    #cfg for RL models
    params=OrderedDict()
    params['total_num_epochs'] = [47000]
    #params['state_size'] = [200, 200, 200, 200, 200, 200, 200, 200]
    #params['state_size'] = [200, 200, 200, 200]
    params['state_size'] = [50]
    params['test_ratio'] = [0.33]
    params['num_samples'] = [1500, 3500]
    params['batch_size']  = [100]
    params['learning_rate'] = [0.005]
    params['epsilon'] = [1e-3]
    params['max_output_ops'] = [5]
    params['num_features'] = [4]
    #params['train_fn'] = ["np_add"]
    #params['train_fn'] = ["np_avg_val" ,"np_center"]
    params['train_fn'] = ["np_mult"]
    params['model'] = ["RLRNN"]
    params['state_fn'] = ["relu"]
    params['pen_sofmax'] = [False]
    params['augument_grad'] = [False]
    params['max_reward'] = [1000]
    params['relaunch'] = [False]
else:
    raise Exception('Wrong model specified to be run')

#cfg which unlinkely is going to be iterated, but still can be configured

#seed
seed = FLAGS.seed
#for n in range(len(cfg)):
cfg_dicts = [OrderedDict(zip(params, x)) for x in itertools.product(*params.values())]

cmds = [gen_cmd(cdict, seed) for cdict in cfg_dicts]

for ind,cmd in enumerate(cmds):
    print("Lnch[" + str(ind+1) +"]: " + cmd)
    subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT)
