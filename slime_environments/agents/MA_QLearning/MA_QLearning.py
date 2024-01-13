import slime_environments.agents.utils.utils as utils
from slime_environments.environments.SlimeEnvMultiAgent import Slime

import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

import argparse

import json
import numpy as np
import random


def create_agent(params:dict, l_params:dict, train_episodes:int):
    n_actions = len(l_params["actions"])
    population = params['population']
    learner_population = params['learner_population']
    
    # Q_table
    qtable = {str(i): np.zeros([4, n_actions]) for i in range(population, population + learner_population)}

    # DOC dict che tiene conto della frequenza di scelta delle action per ogni episodio {episode: {action: _, action: _, ...}}
    actions_dict = {str(ep): {str(ac): 0 for ac in range(n_actions)} for ep in range(1, train_episodes + 1)}  # DOC 0 = walk, 1 = lay_pheromone, 2 = follow_pheromone
    # DOC dict che tiene conto della frequenza di scelta delle action di ogni agent per ogni episodio {episode: {agent: {action: _, action: _, ...}}}
    action_dict = {str(ep): {str(ag): {str(ac): 0 for ac in range(n_actions)} for ag in range(population, population + learner_population)} for ep in range(1, train_episodes + 1)}
    # DOC dict che tiene conto della reward di ogni agente per ogni episodio {episode: {agent: _}}
    reward_dict = {str(ep): {str(ag): 0 for ag in range(population, population + learner_population)} for ep in range(1, train_episodes + 1)}
    # DOC dict che tiene conto dela dimensioni di ogni cluster per ogni episodio
    cluster_dict = {}
    
    return qtable, actions_dict, action_dict, reward_dict, cluster_dict


def train(env, 
          params:dict, 
          qtable, 
          actions_dict:dict, 
          action_dict:dict, 
          reward_dict:dict, 
          cluster_dict:dict,
          train_episodes:int, 
          train_log_every, 
          alpha:float, 
          gamma:float, 
          decay:float,
          epsilon:float,
          output_file):
    # TRAINING
    print("Start training...")
    
    old_s = {}  # DOC old state for each agent {agent: old_state}
    for ep in range(1, train_episodes + 1):
        env.reset()
        
        for tick in range(1, params['episode_ticks'] + 1):
            for agent in env.agent_iter(max_iter=params['learner_population']):
                cur_state, reward, _, _, _ = env.last(agent)
                cur_s = utils.state_to_int_map(cur_state)
                
                if ep == 1 and tick == 1:
                    action = env.action_space(agent).sample()
                else:
                    old_value = qtable[agent][old_s[agent]][action]
                    next_max = np.max(qtable[agent][cur_s])  # QUESTION: was with [action] too
                    new_value = (1 - alpha) * old_value + alpha * (reward + gamma * next_max)
                    qtable[agent][old_s[agent]][action] = new_value

                    if random.uniform(0, 1) < epsilon:
                        # action = np.random.randint(0, 2)
                        action = env.action_space(agent).sample()
                    else:
                        action = np.argmax(qtable[agent][cur_s])
                env.step(action)

                old_s[agent] = cur_s

                actions_dict[str(ep)][str(action)] += 1
                action_dict[str(ep)][str(agent)][str(action)] += 1
                reward_dict[str(ep)][str(agent)] += round(reward, 2)
                
            env.move()
            env._evaporate()
            env._diffuse()
            env.render()
            #print(json.dumps(action_dict, indent=2))
        epsilon *= decay
        cluster_dict[str(ep)] = round(env.avg_cluster(), 2)
        
        if ep % train_log_every == 0:
            print(f"EPISODE: {ep}")
            print(f"\tepsilon: {epsilon}")
            #print(f"\tepisode reward: {reward_episode}")
            # From NetlogoDataAnalysis: Episode, Tick, Avg cluster size X tick, move-toward-chemical (2), random-walk (0), drop-chemical (1), (learner 0)-move-toward-chemical, ..., Avg reward X episode
            
            with open(output_file, 'a') as f:
                f.write(f"{ep}, {params['episode_ticks'] * ep}, {cluster_dict[str(ep)]}, {actions_dict[str(ep)]['2']}, {actions_dict[str(ep)]['0']}, {actions_dict[str(ep)]['1']}, ")
                avg_rew = 0
                
                for l in range(params['population'], params['population'] + params['learner_population']):
                    avg_rew += (reward_dict[str(ep)][str(l)] / params['episode_ticks'])
                    f.write(f"{action_dict[str(ep)][str(l)]['2']}, {action_dict[str(ep)][str(l)]['0']}, {action_dict[str(ep)][str(l)]['1']}, ")
                
                avg_rew /= params['learner_population']
                f.write(f"{avg_rew}\n")

    #print(json.dumps(cluster_dict, indent=2))
    print("Training finished!\n")
    
    return env, qtable


def eval(env,
         params:dict, 
         test_episodes:int,
         qtable,
         test_log_every:int,
         epsilon:float,):
    # DOC Evaluate agent's performance after Q-learning
    cluster_dict = {}
    print("Start testing...")
    
    for ep in range(1, test_episodes + 1):
        env.reset()
        for tick in range(1, params['episode_ticks']+1):
            for agent in env.agent_iter(max_iter=params['learner_population']):
                state, _, _, _ = env.last(agent)
                s = utils.state_to_int_map(state.observe())

                if random.uniform(0, 1) < epsilon:
                    # action = np.random.randint(0, 2)
                    action = env.action_space(agent).sample()
                else:
                    action = np.argmax(qtable[agent][s])

                env.step(action)
            env.move()
            env._evaporate()
            env._diffuse()
            env.render()
            
        if ep % test_log_every == 0:
            print(f"EPISODE: {ep}")
            print(f"\tepsilon: {epsilon}")
            # print(f"\tepisode reward: {reward_episode}")
        cluster_dict[str(ep)] = round(env.avg_cluster(), 2)
        
    print(json.dumps(cluster_dict, indent=2))
    print("Testing finished!\n")
    env.close()


def main(args):
    random.seed(args.random_seed)
    np.random.seed(args.random_seed)
    curdir = os.path.dirname(os.path.abspath(__file__))
    
    params, l_params = utils.read_params(args.params_path, args.learning_params_path)
    
    env = Slime(render_mode="human", **params)
    
    output_dir, output_file, alpha, gamma, epsilon, decay, train_episodes, train_log_every, test_episodes, test_log_every = utils.setup(True, curdir, params, l_params)

    qtable, actions_dict, action_dict, reward_dict, cluster_dict = create_agent(params, l_params,train_episodes)
    
    env, qtable = train(env, params, qtable, actions_dict, action_dict, reward_dict, cluster_dict, train_episodes, train_log_every, alpha, gamma, decay, epsilon, output_file)
    
    eval(env, params, test_episodes, qtable, test_log_every, epsilon)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params_path", type=str, default="qLearning-env-params.json", required=False)
    parser.add_argument("--learning_params_path", type=str, default="qLearning-learning-params.json", required=False)
    parser.add_argument("--random_seed", type=int, default=42, required=False)
    
    args = parser.parse_args()
    
    assert args.params_path != "" and os.path.isfile(args.params_path) and args.params_path.endswith(".json"), "[ERROR] params path is empty or is not a file or is not a json file"
    assert args.learning_params_path != "" and os.path.isfile(args.learning_params_path) and args.learning_params_path.endswith(".json"), "[ERROR] learning params path is empty or is not a file or is not a json file"
    
    main(args)
    