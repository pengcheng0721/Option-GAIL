import torch
from model.option_policy import OptionPolicy, Policy
import numpy as np
from typing import Union
import os
import random


def sample_batch(policy: Union[OptionPolicy, Policy], agent, n_step):
    sample = agent.collect(policy.state_dict(), n_step, fixed=False)
    rsum = sum([sxar[-1].sum().item() for sxar in sample]) / len(sample)
    return sample, rsum


def validate(policy: Union[OptionPolicy, Policy], sa_array):
    with torch.no_grad():
        log_pi = 0.
        cs = []
        for s_array, a_array in sa_array:
            if isinstance(policy, OptionPolicy):
                c_array, logp = policy.viterbi_path(s_array, a_array)
                log_pi += logp.item()
                cs.append(c_array.detach().cpu().squeeze(dim=-1).numpy())
            else:
                log_pi += policy.log_prob_action(s_array, a_array).sum().item()
                cs.append([0.])
        log_pi /= len(sa_array)
    return log_pi, cs


def reward_validate(agent, policy: Union[OptionPolicy, Policy], n_sample=-8, do_print=True):
    trajs = agent.collect(policy.state_dict(), n_sample, fixed=False)
    rsums = [tr[-1].sum().item() for tr in trajs]
    steps = [tr[-1].size(0) for tr in trajs]
    if isinstance(policy, OptionPolicy):
        css = [tr[1].cpu().squeeze(dim=-1).numpy() for _, tr in sorted(zip(rsums, trajs), key=lambda d: d[0], reverse=True)]
    else:
        css = None

    info_dict = {
        "r-max": np.max(rsums), "r-min": np.min(rsums), "r-avg": np.mean(rsums),
        "step-max": np.max(steps), "step-min": np.min(steps),
    }
    if do_print:
        print(f"R: [ {info_dict['r-min']:.02f} ~ {info_dict['r-max']:.02f}, avg: {info_dict['r-avg']:.02f} ], "
              f"L: [ {info_dict['step-min']} ~ {info_dict['step-max']} ]")
    return info_dict, css


def lr_factor_func(i_iter, end_iter, start=1., end=0.):
    if i_iter <= end_iter:
        return start - (start - end) * i_iter / end_iter
    else:
        return end


def get_dirs(seed, exp_type="gail", env_type="mujoco", env_name="HalfCheetah-v2", msg="default", is_opt=True):
    assert env_type in ("mini", "mujoco", "rlbench"), f"Error, env_type {env_type} not supported"

    base_log_dir = "./result"
    base_data_dir = "./data"
    rand_str = f"{seed}"

    sample_name = os.path.join(base_data_dir, env_type, f"{env_name}_sample.torch")
    pretrain_name = os.path.join(base_data_dir, env_type, f"{env_name}_pretrained{'-opt' if is_opt else ''}.torch")

    log_dir_root = os.path.join(base_log_dir, env_name, f"{exp_type}{'-opt' if is_opt else ''}", msg, rand_str)
    save_dir = os.path.join(log_dir_root, "model")
    log_dir = os.path.join(log_dir_root, "log")
    os.makedirs(save_dir)
    os.makedirs(log_dir)

    return log_dir, save_dir, sample_name, pretrain_name


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.random.manual_seed(seed)
