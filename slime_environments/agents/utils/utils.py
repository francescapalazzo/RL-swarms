import os
import json
import math
import datetime
import matplotlib.pyplot as plt
from typing import Optional
from tqdm import tqdm
import numpy as np

def read_params(params_path:str, learning_params_path:str):
    params, l_params = dict(), dict()
    try:
        with open(learning_params_path) as f:
            l_params = json.load(f)
    except Exception as e:
        print(f"[ERROR] could not open learning params file: {e}")
    
    try:
        with open(params_path) as f:
            params = json.load(f)
    except Exception as e:
        print(f"[ERROR] could not open learning params file: {e}")
        
    return params, l_params


def state_to_int_map(obs: list):
    if sum(obs) == 0:  # DOC [False, False]
        mapped = sum(obs)  # 0
    elif sum(obs) == 2:  # DOC [True, True]
        mapped = 3
    elif int(obs[0]) == 1 and int(obs[1]) == 0:  # DOC [True, False] ==> si trova in un cluster ma non su una patch con feromone --> difficile succeda
        mapped = 1
    else:
        mapped = 2  # DOC [False, True]
    return mapped


def setup(curdir:str, params:dict, l_params:dict):
    if not os.path.isdir(os.path.join(curdir, "runs")):
        os.makedirs(os.path.join(curdir, "runs"))
    
    filename = l_params['OUTPUT_FILE'].replace("-", "_") + "_" + datetime.datetime.now().strftime("%m_%d_%Y__%H_%M_%S") + ".csv"
    output_file = os.path.join(curdir, "runs", filename)

    # Q-Learning
    alpha = l_params["alpha"]  # DOC learning rate (0 learn nothing 1 learn suddenly)
    gamma = l_params["gamma"]  # DOC discount factor (0 care only bout immediate rewards, 1 care only about future ones)
    epsilon = l_params["epsilon"]  # DOC chance of random action
    decay = l_params["decay"]  # DOC di quanto diminuisce epsilon ogni episode (e.g. 1500 episodes => decay = 0.9995)
    train_episodes = l_params["train_episodes"]
    test_episodes = l_params["test_episodes"]
    train_log_every = l_params["TRAIN_LOG_EVERY"]
    test_log_every = l_params["TEST_LOG_EVERY"]

    with open(output_file, 'w') as f:
        f.write(f"{json.dumps(params, indent=2)}\n")
        f.write("----------\n")
        f.write(f"TRAIN_EPISODES = {train_episodes}\n")
        f.write(f"TEST_EPISODES = {test_episodes}\n")
        f.write("----------\n")
        f.write(f"alpha = {alpha}\n")
        f.write(f"gamma = {gamma}\n")
        f.write(f"epsilon = {epsilon}\n")
        f.write(f"decay = {decay}\n")
        f.write("----------\n")
        # From NetlogoDataAnalysis: Episode, Tick, Avg cluster size X tick, Avg reward X episode, move-toward-chemical, random-walk, drop-chemical, (learner 0)-move-toward-chemical
        f.write(f"Episode, Tick, Avg cluster size X tick, ")
        
        for a in l_params["actions"]:
            f.write(f"{a}, ")
        
        for l in range(params['population'], params['population'] + params['learner_population']):
            for a in l_params["actions"]:
                f.write(f"(learner {l})-{a}, ")
        f.write("Avg reward X episode, loss, learning rate\n")
    
    return output_file, alpha, gamma, epsilon, decay, train_episodes, train_log_every, test_episodes, test_log_every


def calculate_epsilon(type:str, episodes:int, ticks:int, learners:int, epsilon: float, decay:float, epsilon_end:Optional[float]):
    indexes = []
    values = []
    
    pbar = tqdm(range(episodes*ticks))
    for ep in range(1, episodes + 1):
        for tick in range(1, ticks + 1):
            for agent in range(learners):
                index = agent + tick * learners + ep * ticks * learners
                indexes.append(index)
                if ep == 1 and tick == 1:
                    pass
                else:
                    if type.lower() in "normal":
                        epsilon *= decay
                    elif type.lower() == "esponential":
                        epsilon = epsilon_end + (epsilon - epsilon_end) * math.exp(-1. * ep * decay)
                    
                values.append(epsilon)
            pbar.update(1)
                
    plt.plot(indexes, values, marker='o')
    plt.xlabel('Steps')
    plt.ylabel('epsilon value')
    plt.show()
    print(f"Final value: {epsilon}")
    

def positional_encoding(sequence_length, d_model):
    positions = np.arange(sequence_length)[:, np.newaxis]
    angles = np.arange(d_model)[np.newaxis, :] / np.power(10000, 2 * (np.arange(d_model) // 2) / d_model)
    encoding = positions * angles

    encoding[:, 0::2] = np.sin(encoding[:, 0::2])  # Colonne pari: seno
    encoding[:, 1::2] = np.cos(encoding[:, 1::2])  # Colonne dispari: coseno

    return encoding


def update_summary(output_file, ep, params, cluster_dict, actions_dict, action_dict, reward_dict):
    with open(output_file, 'a') as f:
        f.write(f"{ep}, {params['episode_ticks'] * ep}, {cluster_dict[str(ep)]}, {actions_dict[str(ep)]['2']}, {actions_dict[str(ep)]['0']}, {actions_dict[str(ep)]['1']}, ")
        avg_rew = 0

        for l in range(params['population'], params['population'] + params['learner_population']):
            avg_rew += (reward_dict[str(ep)][str(l)] / params['episode_ticks'])
            f.write(f"{action_dict[str(ep)][str(l)]['2']}, {action_dict[str(ep)][str(l)]['0']}, {action_dict[str(ep)][str(l)]['1']}, ")

        avg_rew /= params['learner_population']
        f.write(f"{avg_rew}\n")


def calc_final_lr(base_lr, gamma, step_size, iterations, batch_size):
    print(base_lr * gamma ** ((iterations / batch_size) // step_size) )

    
if __name__ == "__main__":
    calc_final_lr(1e-3, .9945, 1, 51200, 128)
    calculate_epsilon("esponential", 100, 512, 100, 0.9, 20e-9, 0.0)
