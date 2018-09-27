#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import tensorflow as tf

import matplotlib.pyplot as plt
import time
import os

os.environ["CUDA_VISIBLE_DEVICES"] = '1'

import urllib2
from urllib2 import urlopen
script_path = "/home/zhangchao/cvs/reader.py"
import sys
sys.path.append(script_path)
import reader
#from tensorflow.models.rnn.ptb import reader


# In[2]:


file_url = 'https://raw.githubusercontent.com/jcjohnson/torch-rnn/master/data/tiny-shakespeare.txt'
file_name = "tinyshakespeare.txt"


proxy = urllib2.ProxyHandler({'https': '172.17.225.138:1087'})
opener = urllib2.build_opener(proxy)
urllib2.install_opener(opener)
#print urllib2.urlopen('https://www.google.com.hk').read()

if not os.path.exists(file_name):
    data = urlopen(file_url).read()
    with open(file_name, 'w') as file:
        file.write(data)

with open(file_name,'r') as f:
    raw_data = f.read()

print("Data length:", len(raw_data))
#print raw_data
vocab = set(raw_data)        
#print vocab
vocab_size = len(vocab)        
print vocab_size
idx_to_vocab = dict(enumerate(vocab))
#print(idx_to_vocab)
vocab_to_idx = dict(zip(idx_to_vocab.values(), idx_to_vocab.keys()))
#print vocab_to_idx

data = [vocab_to_idx[c] for c in raw_data]
#print data
print len(data)
del raw_data

def gen_epochs(n, num_steps, batch_size):
    for i in range(n):
        #yield reader.ptb_iterator(data, batch_size, num_steps)
        yield reader.ptb_producer(data, batch_size, num_steps)
def reset_graph():
    if 'sess' in globals() and sess:
        sess.close()
    tf.reset_default_graph()
    
def train_network(g, num_epochs, num_steps = 200, batch_size = 32, verbose = True, save=False):
    tf.set_random_seed(2345)
    #sv = tf.train.Supervisor()
    #with  sv.managed_session() as sess:
    with tf.Session() as sess:
    #with tf.train.MonitoredTrainingSession() as sess:

        sess.run(tf.global_variables_initializer())

        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)

        training_losses = []
        for idx, epoch in enumerate(gen_epochs(num_epochs, num_steps, batch_size)):
            training_loss = 0 
            steps = 0
            training_state = None

            #for x, y in epoch:
            for i in range(len(epoch)):
                x = epoch[0]
                y = epoch[1]
                print ("in epoch loop %d" % steps)
                try:
                    while not coord.should_stop():
                        X, Y = sess.run([x, y])

                except tf.errors.OutOfRangeError:
                    print('Done training -- epoch limit reached')

                finally:
                    # When done, ask the threads to stop.
                    coord.request_stop()

                print ("after sess.run[x,y]")
                steps += 1
                feed_dict = {g['x']: X, g['y']: Y}
                if training_state is not None:
                    feed_dict[g['init_state']] = training_state
                training_loss_ , training_state, _ = sess.run([g['total_loss'],
                                                            g['final_state'],
                                                            g['train_step']],
                                                             feed_dict
                                                            )    
                training_loss += training_loss_
            if verbose:
                print("Average training loss for epoch", idx, ":", training_loss / steps)
            training_losses.append(training_loss / steps)

        coord.join(threads)

        if isnistance(save, str):
            g['saver'].save(sess, save)
    return training_losses
            
            


# In[8]:
def build_multilayer_lstm_graph_with_list(
    state_size = 100,
    num_classes = vocab_size,
    batch_size = 32,
    num_steps = 200,
    num_layers = 3,
    learning_rate = 1e-4):
    reset_graph()
    
    x = tf.placeholder(tf.int32, [batch_size, num_steps], name="input_placeholder")
    y = tf.placeholder(tf.int32, [batch_size, num_steps], name='labels_placeholder')
    
    embeddings = tf.get_variable('embedding_matrix', [num_classes, state_size])
    rnn_inputs = [tf.squeeze(i) for i in tf.split(tf.nn.embedding_lookup(embeddings, x), num_steps, 1)]
    
    cell = tf.nn.rnn_cell.LSTMCell(state_size, state_is_tuple=True)
    cell = tf.nn.rnn_cell.MultiRNNCell([cell] * num_layers, state_is_tuple=True)
    
    init_state = cell.zero_state(batch_size, tf.float32)
    rnn_outputs, final_state = tf.nn.static_rnn(cell, rnn_inputs, initial_state=init_state)
    
    with tf.variable_scope('softmax'):
        W = tf.get_variable('W', [state_size, num_classes])
        b = tf.get_variable('b', [num_classes], initializer=tf.constant_initializer(0.0))
    logits = [tf.matmul(rnn_output, W) + b for rnn_output in rnn_outputs]
    
    y_as_list = [tf.squeeze(i, squeeze_dims=[1]) for i in tf.split(y, num_steps, 1)]
    
    loss_weights = [tf.ones([batch_size]) for i in range(num_steps)]
    losses = tf.contrib.legacy_seq2seq.sequence_loss_by_example(logits, y_as_list, loss_weights)
    total_loss = tf.reduce_mean(losses)

    train_step = tf.train.AdadeltaOptimizer(learning_rate).minimize(total_loss)
    
    return dict(
        x = x, 
        y = y,
        final_state = final_state,
        total_loss = total_loss,
        train_step = train_step
    )  
    
    


# for idx, epoch in  enumerate(gen_epochs(3, 200, 32)):
#     #tf.map_fn(lambda x: x, epoch)
#     #x_unpacked = tf.unstack(tf.reshape(epoch,[-1]))
#     for X,Y in epoch:
#         #print ("type(idx) is %s " % (type(idx)))
#         #X = epoch[0]
#         #Y = epoch[1]
#         #print ("type(epoch) is %s " % (type(epoch)))
#         #print ("epoch len is %d " % (len(epoch)))
#         print ("epoch[0] is %s" % X)
#         print ("epoch[1] is %s " %  Y)


# In[ ]:


g = build_multilayer_lstm_graph_with_list()
t = time.time()
train_network(g, 3)
print("It took", time.time() - t , "seconds to train for 3 epochs.")


# In[93]:


#from tensorflow.contrib import rnn 
def build_basic_rnn_graph_with_list(
    state_size = 100,
    num_classes = vocab_size,
    batch_size = 32,
    num_steps = 200,
    num_layers = 3,
    learning_rate = 1e-4):
    
    reset_graph()
    x = tf.placeholder(tf.int32, [batch_size, num_steps], name='input_placeholder')
    y = tf.placeholder(tf.int32, [batch_size, num_steps], name='labels_placeholder')
    
    x_one_hot = tf.one_hot(x, num_classes)
    print x_one_hot.shape
    rnn_inputs = [tf.squeeze(i, squeeze_dims=[1]) for i in tf.split(x_one_hot, num_steps, 1)]
    
    cell = tf.nn.rnn_cell.BasicRNNCell(state_size)
    #cell = tf.nn.rnn_cell.MultiRNNCell([cell] * num_layers, state_is_tuple=True)
    init_state = cell.zero_state(batch_size, tf.float32)
    rnn_outputs , final_state = tf.nn.static_rnn(cell, rnn_inputs, initial_state=init_state)
    
    with tf.variable_scope('softmax'):
        W = tf.get_variable('W', [state_size, num_classes])
        b = tf.get_variable('b', [num_classes], initializer=tf.constant_initializer(0.0))
    logits = [tf.matmul(rnn_output,W) + b for rnn_output in rnn_outputs]
    
    y_as_list = [tf.squeeze(i, squeeze_dims=[1]) for i in tf.split(y, num_steps, 1)]
    
    loss_weights = [tf.ones([batch_size]) for i in range(num_steps)]
    losses = tf.contrib.legacy_seq2seq.sequence_loss_by_example(logits, y_as_list, loss_weights)
    total_loss = tf.reduce_mean(losses)
    train_step = tf.train.AdadeltaOptimizer(learning_rate).minimize(total_loss)
    return dict(
    x = x,
    y = y,
    init_state = init_state,
    final_state = final_state,
    total_loss = total_loss,
    train_step = train_step
    )
    
    
    


# In[94]:


t = time.time()
build_basic_rnn_graph_with_list()
print("It took", time.time() - t, "seconds to build the graph")



# In[3]:




# In[96]:


t = time.time()
build_multilayer_lstm_graph_with_list()
print("It took", time.time() - t, "seconds to build the graph.")


# In[97]:


def build_multilayer_lstm_graph_with_dynamic_rnn(
    state_size = 100,
    num_classes = vocab_size,
    batch_size = 32,
    num_steps = 200,
    num_layers = 3,
    learning_rate = 1e-4):
    reset_graph()
    x = tf.placeholder(tf.int32, [batch_size, num_steps], name='input_placeholder')
    y = tf.placeholder(tf.int32, [batch_size, num_steps], name='labels_palceholder')
    
    embeddings = tf.get_variable('embedding_matrix', [num_classes, state_size])
    
    # Note that our inputs are no longer a list, but a tensor of dims batch_size x num_steps x state_size
    
    rnn_inputs = tf.nn.embedding_lookup(embeddings, x)
    
    cell = tf.nn.rnn_cell.LSTMCell(state_size, state_is_tuple=True)
    cell = tf.nn.rnn_cell.MultiRNNCell([cell] * num_layers, state_is_tuple=True)
    init_state = cell.zero_state(batch_size, tf.float32)
    rnn_outputs, final_state = tf.nn.dynamic_rnn(cell, rnn_inputs, initial_state=init_state)
    
    with tf.variable_scope('softmax'):
        W = tf.get_variable('W', [state_size, num_classes])
        b = tf.get_variable('b', [num_classes], initializer=tf.constant_initializer(0.0))
    
    # reshape rnn_outputs and y so we can get the logits in a single matmul
    rnn_outputs = tf.reshape(rnn_outputs, [-1, state_size])
    y_reshpaed = tf.reshape(y, [-1])
    
    logits = tf.matmul(rnn_outputs, W) + b
    
    total_loss = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logits, labels=y_reshpaed))
    train_step = tf.train.AdamOptimizer(learning_rate).minimize(total_loss)
    return dict(
        x =x,
        y = y,
        init_state = init_state,
        final_state = final_state,
        total_loss = total_loss,
        train_step = train_step
    )
    
    
    
    


# In[98]:


t = time.time()
build_multilayer_lstm_graph_with_dynamic_rnn()
print("It took", time.time() - t, "seconds to build the graph.")


# In[100]:


g = build_multilayer_lstm_graph_with_list()
t = time.time()
train_network(g, 3)
print("It took", time.time() - t , "seconds to train for 3 epochs.")


# In[ ]:




