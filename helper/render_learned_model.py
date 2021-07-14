#!/usr/bin/env python3

import os
import torch
from model.option_gail import OptionGAIL, GAIL
from utils.state_filter import StateFilter
import matplotlib.pyplot as plt
from utils.config import Config
from utils.agent import loop, option_loop
import sys


def init_figure(dim_c, dpi=192):
    a = plt.figure(dpi=dpi)
    ax = a.gca()
    ax.set_yticks(range(dim_c))
    ax.set_ylim(-0.2, dim_c - 0.8)
    return a, ax


def display_model(model_path, config_path=None):
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Error, model file {model_path} not exists")
    if config_path is None:
        config_path = os.path.join(os.path.dirname(model_path), "config.log")

    config = Config().load_saved(config_path)
    policy_state, filter_state = torch.load(model_path, map_location="cpu")

    config.device = "cpu"
    use_option = config.use_option
    env_name = config.env_name
    env_type = config.env_type
    use_state_filter = config.use_state_filter

    if env_type == "mujoco":
        from envir.mujoco_env import MujocoEnv
        env = MujocoEnv(env_name).init(display=True)
    else:
        from envir.rlbench_env import RLBenchEnv
        env = RLBenchEnv(env_name).init(display=True)

    dim_s, dim_a = env.state_action_size()
    gail = OptionGAIL(config, dim_s=dim_s, dim_a=dim_a) if use_option else GAIL(config, dim_s=dim_s, dim_a=dim_a)
    try:
        gail.load_state_dict(policy_state)
    except RuntimeError:
        gail.policy.load_state_dict(policy_state)
    policy = gail.policy

    state_filter = StateFilter(enable=use_state_filter)
    state_filter.load_state_dict(filter_state)
    loop_func = option_loop if use_option else loop

    if use_option:
        plt.figure("task class info")
        plt.ion()
    while True:
        sxar = loop_func(env, policy, state_filter, fixed=True)
        if use_option:
            a, ax = init_figure(policy.dim_c)
            ax.plot(sxar[1][1:].cpu().squeeze().numpy())
            plt.pause(0.1)
        print(f"R-sum: {sxar[-1].sum().item()}; L-step: {sxar[-1].size(0)}")


if __name__ == "__main__":
    model_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

    display_model(model_path, config_path)
