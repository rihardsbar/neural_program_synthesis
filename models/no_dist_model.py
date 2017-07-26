import numpy as np
import tensorflow as tf
from functools import reduce
import matplotlib.pyplot as plt
from tensorflow.python import debug as tf_debug
from tensorflow.python.framework import ops
import pprint
from numpy.random import RandomState
import random
import time
import os
import sys
import datetime

#model flags
tf.flags.DEFINE_boolean("debug", False, "weather run in a dubg mode")

tf.flags.DEFINE_integer("state_size", 50, "weather to norm grads")    
tf.flags.DEFINE_integer("num_samples", 1500, "weather to norm grads")
tf.flags.DEFINE_integer("batch_size", 100, "weather to norm grads")

tf.flags.DEFINE_float("learning_rate", 0.005, "weather to norm grads")
tf.flags.DEFINE_float("grad_norm", 10e2, "weather to norm grads")
tf.flags.DEFINE_integer("max_output_ops", 5, "weather to norm grads")

tf.flags.DEFINE_integer("num_features", 3, "weather to norm grads")
tf.flags.DEFINE_string("train_fn", "np_mult", "weather to norm grads")
tf.flags.DEFINE_boolean("norm", True, "weather to norm grads")

tf.flags.DEFINE_integer("seed", round(random.random()*100000), "the global simulation seed for np and tf")
tf.flags.DEFINE_string("name", "predef_sim_name" , "name of the simulation")

datatype = tf.float64
FLAGS = tf.flags.FLAGS


def variable_summaries(var):
  """Attach a lot of summaries to a Tensor (for TensorBoard visualization)."""
  with tf.name_scope(var.name.replace(":","_")):
    mean = tf.reduce_mean(var)
    tf.summary.scalar('mean', mean)
    tf.summary.scalar('stddev', tf.sqrt(tf.reduce_mean(tf.square(var - mean))))
    tf.summary.scalar('max', tf.reduce_max(var))
    tf.summary.scalar('min', tf.reduce_min(var))
    tf.summary.histogram('histogram', var)

def write_no_tf_summary(writer, tag, val, step):
   summary=tf.Summary()
   summary.value.add(tag=tag, simple_value = val)
   writer.add_summary(summary, step)
    
def split_train_test (x, y , test_ratio):
    
    if y.shape != x.shape:
        raise Exception('Model expects x and y shapes to be the same')
    
    test_len  = int(x.shape[0]*test_ratio)
    train_len = x.shape[0] - test_len

    x_train = x[0:train_len][:]
    x_test  = x[-test_len:][:]
    y_train = y[0:train_len][:]
    y_test  = y[-test_len:][:]
    
    train_shape = (train_len, x.shape[1])
    test_shape = (test_len, x.shape[1])
    
    if test_ratio == 0:
        x_test = np.zeros(test_shape)
        y_test = np.zeros(test_shape)

    if y_train.shape != train_shape or x_train.shape != train_shape or x_test.shape != test_shape or y_test.shape != test_shape:
        raise Exception('One of the conversion test/train shapes gone wrong')
    
    return  x_train, x_test, y_train, y_test

#helpder func
def get_time_hhmmss(dif):
    m, s = divmod(dif, 60)
    h, m = divmod(m, 60)
    time_str = "%02d:%02d:%02d" % (h, m, s)
    return time_str


#sample gen functions
def np_add(vec):
    return reduce((lambda x, y: x + y),vec)

def np_mult(vec):
    return reduce((lambda x, y: x * y),vec)

def np_stall(vec):
    return vec

def samples_generator(fn, shape, rng, seed):
    '''
    Generate random samples for the model:
    @fn - function to be applied on the input features to get the ouput
    @shape - shape of the features matrix (num_samples, num_features)
    @rng - range of the input features to be generated within (a,b)
    Outputs a tuple of input and output features matrix
    '''
    prng = RandomState(seed)
    x = (rng[1] - rng[0]) * prng.random_sample(shape) + rng[0]
    y = np.apply_along_axis(fn, 1, x).reshape((shape[0],-1))
    z = np.zeros((shape[0],shape[1] - y.shape[1]))
    y = np.concatenate((y, z), axis=1)
    
    return x,y

def get_syn_fn(fn_name):
    if   fn_name == "np_add":   return np_add
    elif fn_name == "np_mult":  return np_mult
    elif fn_name == "np_stall": return np_stall
    else: raise Exception('Function passed by the flag to be synthesised has not been defined')

#configuraion constants
global_cfg = dict(
    total_num_epochs = 10000000,
    iters_per_epoch = 1,
    num_of_operations = 3,
    samples_value_rng = (-100, 100),
    test_ratio = 0.33333,
    param_init = 0.1,
    epsilon=1e-6,
    test_cycle = 150,
    convergance_check_epochs = 5000,
    sim_start_time = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S"),

    #flagged
    state_size = FLAGS.state_size,
    num_samples = FLAGS.num_samples,
    batch_size  = FLAGS.batch_size,

    learning_rate = FLAGS.learning_rate,
    grad_norm = FLAGS.grad_norm,
    max_output_ops = FLAGS.max_output_ops,

    num_features = FLAGS.num_features,
    train_fn = get_syn_fn(FLAGS.train_fn),
    norm = FLAGS.norm,

    seed = FLAGS.seed,
    name = FLAGS.name
)
global_cfg['num_epochs'] = global_cfg['total_num_epochs'] // global_cfg['iters_per_epoch']

#populate the global env with dict variables - !!can lead to nasty bugs
for name, value in global_cfg.items():
    globals()[name] = value

#craete log and dumpl globals
try:
    os.mkdir('./summaries/' + FLAGS.name)
except FileExistsError as err:
    print("Dir already exists")

stdout_org = sys.stdout
sys.stdout = open('./summaries/' + FLAGS.name  + '/log.log', 'w')
print("###########Global dict is###########")
pprint.pprint(globals(), depth=3)
print("###########CFG dict is###########")
pprint.pprint(global_cfg, depth=3)
print("#############################")
#sys.stdout = stdout_org

#model operations
def tf_multiply(inpt):
    return tf.reshape( tf.reduce_prod(inpt, axis = 1, name = "tf_mult"), [batch_size, -1], name = "tf_mult_reshape")

def tf_add(inpt):
    return  tf.reshape( tf.reduce_sum(inpt, axis = 1, name = "tf_add"), [batch_size, -1], name = "tf_add_reshape")

def tf_stall(a):
    return a

#model constants
dummy_matrix = tf.zeros([batch_size, num_features], dtype=datatype, name="dummy_constant")

#model placeholders
batchX_placeholder = tf.placeholder(datatype, [batch_size, None], name="batchX")
batchY_placeholder = tf.placeholder(datatype, [batch_size, None], name="batchY")

init_state = tf.placeholder(datatype, [batch_size, state_size], name="init_state")


#set random seed
tf.set_random_seed(seed)

#model parameters
W = tf.Variable(tf.truncated_normal([state_size+num_features, state_size], -1*param_init, param_init, dtype=datatype), dtype=datatype, name="W")
b = tf.Variable(np.zeros((state_size)), dtype=datatype, name="b")
variable_summaries(W)
variable_summaries(b)

W2 = tf.Variable(tf.truncated_normal([state_size, num_of_operations], -1*param_init, param_init, dtype=datatype),dtype=datatype, name="W2")
b2 = tf.Variable(np.zeros((num_of_operations)), dtype=datatype, name="b2")
variable_summaries(W2)
variable_summaries(b2)

    #forward pass
def run_forward_pass(mode="train"):
    current_state = init_state

    output = batchX_placeholder

    outputs = []

    softmaxes = []
    
    #printtf = tf.Print(output, [output], message="Strated cycle")
    #output = tf.reshape( printtf, [batch_size, -1], name = "dummu_rehap")
    
    for timestep in range(max_output_ops):
        print("timestep " + str(timestep))
        current_input = output



        input_and_state_concatenated = tf.concat([current_input, current_state], 1, name="concat_input_state")  # Increasing number of columns
        next_state = tf.tanh(tf.add(tf.matmul(input_and_state_concatenated, W, name="input-state_mult_W"), b, name="add_bias"), name="tanh_next_state")  # Broadcasted addition
        #next_state = tf.nn.relu(tf.add(tf.matmul(input_and_state_concatenated, W, name="input-state_mult_W"), b, name="add_bias"), name="relu_next-state")  # Broadcasted addition
        current_state = next_state

        #calculate softmax and produce the mask of operations
        logits = tf.add(tf.matmul(next_state, W2, name="state_mul_W2"), b2, name="add_bias2") #Broadcasted addition
        softmax = tf.nn.softmax(logits, name="get_softmax")
        #argmax = tf.argmax(softmax, 1)
        '''
        print(logits)
        print(softmax)
        print(argmax)
        '''
        #perform ops
        add   = tf_add(current_input)
        mult  = tf_multiply(current_input)
        stall = tf_stall(current_input)
        #add = tf.reshape( tf.reduce_prod(current_input, axis = 1), [batch_size, -1])
        #mult = tf.reshape( tf.reduce_sum(current_input, axis = 1), [batch_size, -1])
        #stall = current_input
        #values = tf.concat([add, mult, stall], 1)
        #values = tf.concat([add, mult, stall], 1, name="concact_op_values")
        #values = tf.cast(values,dtype=datatype)
        #get softmaxes for operations
        #add_softmax = tf.slice(softmax, [0,0], [batch_size,1])
        #mult_softmax = tf.slice(softmax, [0,1], [batch_size,1])
        #stall_softmax = tf.slice(softmax, [0,2], [batch_size,1])
        #produce output matrix
        #onehot  = tf.one_hot(argmax_dum, num_of_operations)
        #stall_width = tf.shape(stall)[1]
        #stall_select = tf.slice(onehot, [0,2], [batch_size,1])
        #mask_arr = [onehot]
        #for i in range(num_features-1):
        #    mask_arr.append(stall_select)
        #mask = tf.concat(mask_arr, 1)
        #argmax = tf.reshape( softmax, [batch_size, -1])
        #mask = onehot
        #mask = tf.cast(mask, dtype=datatype)
        #mask = tf.cast(mask, tf.bool)
        #apply mask
        #output = tf.boolean_mask(values,mask)
        #in test change to hardmax
        if mode is "test":
            argmax  = tf.argmax(softmax, 1, )
            softmax  = tf.one_hot(argmax, num_of_operations, dtype=datatype)
        #in the train mask = saturated softmax for all ops. in test change it to onehot(hardmax)
        add_softmax   = tf.slice(softmax, [0,0], [batch_size,1], name="slice_add_softmax_val")
        mult_softmax  = tf.slice(softmax, [0,1], [batch_size,1], name="slice_mult_softmax_val")
        stall_softmax = tf.slice(softmax, [0,2], [batch_size,1], name="stall_mult_softmax_val")

        add_width   = tf.shape(add, name="add_op_shape")[1]
        mult_width  = tf.shape(mult, name="mult_op_shape")[1]
        stall_width = tf.shape(stall, name="stall_op_shape")[1]


        add_final   = tf.multiply(add, add_softmax, name="mult_add_softmax")
        mult_final  = tf.multiply(mult,mult_softmax, name="mult_mult_softmax")
        stall_final = tf.multiply(stall, stall_softmax, name="mult_stall_softmax")

        ##conact add and mult results with zeros matrix
        add_final = tf.concat([add_final, tf.slice(dummy_matrix, [0,0], [batch_size, num_features - add_width], name="slice_dum_add")], 1, name="concat_add_op_dummy_zeros") 
        mult_final = tf.concat([mult_final, tf.slice(dummy_matrix, [0,0], [batch_size, num_features - mult_width], name="slice_dum_mult")], 1, name="concat_mult_op_dummy_zeros") 


        output = tf.add(add_final, mult_final, name="add_final_op_mult_add")
        output =  tf.add(output, stall_final, name="add_final_op_stall")
        outputs.append(output)
        softmaxes.append(softmax)
    #printtf = tf.Print(output, [output], message="Finished cycle")
    #output = tf.reshape( printtf, [batch_size, -1], name = "dummu_rehap")
    return output, current_state, softmax, outputs, softmaxes

#cost function
def calc_loss(output):
    #reduced_output = tf.reshape( tf.reduce_sum(output, axis = 1, name="red_output"), [batch_size, -1], name="resh_red_output")
    math_error = tf.multiply(tf.constant(0.5, dtype=datatype), tf.square(tf.subtract(output , batchY_placeholder, name="sub_otput_batchY"), name="squar_error"), name="mult_with_0.5")
    
    total_loss = tf.reduce_sum(math_error, name="red_total_loss")
    return total_loss, math_error

output_train, current_state_train, softmax_train, outputs_train, softmaxes_train = run_forward_pass(mode = "train")
total_loss_train, math_error_train = calc_loss(output_train)

output_test, current_state_test, softmax_test, outputs_test, softmaxes_test = run_forward_pass(mode = "test")
total_loss_test, math_error_test = calc_loss(output_test)

grads_raw = tf.gradients(total_loss_train, [W,b,W2,b2], name="comp_gradients")

#clip gradients by value and add summaries
if norm:
    print("norming the grads")
    grads, norms = tf.clip_by_global_norm(grads_raw, grad_norm)
    variable_summaries(norms)
else:
    grads = grads_raw

for grad in grads: variable_summaries(grad)


train_step = tf.train.AdamOptimizer(learning_rate, epsilon ,name="AdamOpt").apply_gradients(zip(grads, [W,b,W2,b2]), name="min_loss")
print("grads are")
print(grads)

#pre training setting
np.set_printoptions(precision=3, suppress=True)
#train_fn = np_mult
#train_fn = np_stall
x,y = samples_generator(train_fn, (num_samples, num_features) , samples_value_rng, seed)
x_train, x_test, y_train, y_test = split_train_test (x, y , test_ratio)
num_batches = x_train.shape[0]//batch_size
num_test_batches = x_test.shape[0]//batch_size
print("num batches train:", num_batches)
print("num batches test:", num_test_batches)
#model training

#create a saver to save the trained model
saver=tf.train.Saver(var_list=tf.trainable_variables())

#Enable jit
config = tf.ConfigProto()
config.graph_options.optimizer_options.global_jit_level = tf.OptimizerOptions.ON_1
#define congergance check list
last_train_losses = []

with tf.Session(config=config) as sess:
    # Merge all the summaries and write them out 
    merged = tf.summary.merge_all()
    train_writer = tf.summary.FileWriter('./summaries/' + FLAGS.name ,sess.graph)
    ##enable debugger if necessary
    if (FLAGS.debug):
        print("Running in a debug mode")
        sess = tf_debug.LocalCLIDebugWrapperSession(sess)
        sess.add_tensor_filter("has_inf_or_nan", tf_debug.has_inf_or_nan)

    #init the var
    sess.run(tf.global_variables_initializer())
    #plt.ion()
    #plt.figure()
    #plt.show() 
    #Init vars:
    _W = sess.run([W])
    _W2 = sess.run([W2])
    print(W.eval())
    print(W2.eval())
    globalstartTime = time.time()
    for epoch_idx in range(num_epochs):
        startTime = time.time()
        loss_list_train_soft = [0,0]
        loss_list_train_hard = [0,0]
        loss_list_test_soft = [0,0]
        loss_list_test_hard = [0,0]
        summary = None
        
        _current_state_train = np.zeros((batch_size, state_size))
        _current_state_test = np.zeros((batch_size, state_size))

            #backprop and test training set for softmax and hardmax loss
        for batch_idx in range(num_batches):
                start_idx = batch_size * batch_idx
                end_idx   = batch_size * batch_idx + batch_size

                batchX = x_train[start_idx:end_idx]
                batchY = y_train[start_idx:end_idx]

            
                if epoch_idx % test_cycle != 0 :
                    _total_loss_train, _train_step, _current_state_train, _output_train, _grads, _softmaxes_train, _math_error_train = sess.run([total_loss_train, train_step, current_state_train, output_train, grads, softmaxes_train, math_error_train],
                        feed_dict={
                            init_state:_current_state_train,
                            batchX_placeholder:batchX,
                            batchY_placeholder:batchY
                        })
                    loss_list_train_soft.append(_total_loss_train)
                
                else :
                    summary, _total_loss_train, _train_step, _current_state_train, _output_train, _grads, _softmaxes_train, _math_error_train = sess.run([merged, total_loss_train, train_step, current_state_train, output_train, grads, softmaxes_train, math_error_train],
                    feed_dict={
                        init_state:_current_state_train,
                        batchX_placeholder:batchX,
                        batchY_placeholder:batchY
                    })
                    loss_list_train_soft.append(_total_loss_train)
                
                    _total_loss_test, _current_state_test, _output_test, _softmaxes_test, _math_error_test = sess.run([total_loss_test, current_state_test, output_test, softmaxes_test, math_error_test],
                        feed_dict={
                            init_state:_current_state_test,
                            batchX_placeholder:batchX,
                            batchY_placeholder:batchY
                        })
                    loss_list_train_hard.append(_total_loss_test)
        ##save loss for the convergance chessing        
        reduced_loss_train_soft = reduce(lambda x, y: x+y, loss_list_train_soft)
        last_train_losses.append(reduced_loss_train_soft)
        ##every 'test_cycle' epochs test the testing set for sotmax/harmax loss
        if epoch_idx % test_cycle == 0 :
            _current_state_train = np.zeros((batch_size, state_size))
            _current_state_test = np.zeros((batch_size, state_size))
            for batch_idx in range(num_test_batches):
                    start_idx = batch_size * batch_idx
                    end_idx   = batch_size * batch_idx + batch_size

                    batchX = x_test[start_idx:end_idx]
                    batchY = y_test[start_idx:end_idx]

                    _total_loss_train, _current_state_train = sess.run([total_loss_train, current_state_train],
                        feed_dict={
                            init_state:_current_state_train,
                            batchX_placeholder:batchX,
                            batchY_placeholder:batchY
                        })
                    loss_list_test_soft.append(_total_loss_train)

                    _total_loss_test, _current_state_test = sess.run([total_loss_test, current_state_test],
                        feed_dict={
                            init_state:_current_state_test,
                            batchX_placeholder:batchX,
                            batchY_placeholder:batchY
                        })
                    loss_list_test_hard.append(_total_loss_test)

            #save model            
            saver.save(sess, './summaries/' + FLAGS.name + '/model/',global_step=epoch_idx)
            #write variables/loss summaries after all training/testing done
            train_writer.add_summary(summary, epoch_idx)
            write_no_tf_summary(train_writer, "Softmax_train_loss", reduced_loss_train_soft, epoch_idx)
            write_no_tf_summary(train_writer, "Hardmax_train_loss", reduce(lambda x, y: x+y, loss_list_train_hard), epoch_idx)
            write_no_tf_summary(train_writer, "Sotfmax_test_loss", reduce(lambda x, y: x+y, loss_list_test_soft), epoch_idx)
            write_no_tf_summary(train_writer, "Hardmax_test_loss", reduce(lambda x, y: x+y, loss_list_test_hard), epoch_idx)

        print("")
        #harmax test
        '''
        print(" ")
        print("output_train\t\t\t\t\toutput_test")
        print(np.column_stack((_output, _output_test)))
        print("x\t\t\\t\t\t\t\y")
        print(np.column_stack((batchX, batchY)))
        print("softmaxes_train\t\t\t\t\softmaxes_test")
        print(np.column_stack((_softmaxes, _softmaxes_test)))
        print("mat_error_train\t\t\t\t\math_error_test")
        print(np.column_stack((_math_error, _math_error_test)))
        '''
        print("Epoch",epoch_idx)
        print("Softmax train loss\t", reduced_loss_train_soft)
        print("Hardmax train loss\t", reduce(lambda x, y: x+y, loss_list_train_hard))
        print("Sotfmax test loss\t", reduce(lambda x, y: x+y, loss_list_test_soft))
        print("Hardmax test loss\t", reduce(lambda x, y: x+y, loss_list_test_hard))
        print("Epoch time: ", ((time.time() - startTime) % 60), " Global Time: ",  get_time_hhmmss(time.time() - globalstartTime))
        print("func: ", train_fn.__name__, "max_ops: ", max_output_ops, "sim_seed", seed, "tf seed", ops.get_default_graph().seed)
        #print("grads[0] - W", _grads[0][0])
        #print("grads[1] - b", _grads[1][0])
        #print("grads[2] - W2", _grads[2][0])
        #print("grads[3] - b2", _grads[3][0])
        #print("W", W.eval())
        #print("w2" , W2.eval())
        #record execution timeline
        ##check convergance over last 5000 epochs
        if epoch_idx % convergance_check_epochs == 0 and epoch_idx >= convergance_check_epochs: 
            if np.allclose(last_train_losses, last_train_losses[0], equal_nan=True, rtol=1e-05, atol=1e-02):
                print("#################################")
                print("Model has converged, breaking ...")
                print("#################################")
                break
            else:
                print("Reseting the loss conv array")
                last_train_losses = []