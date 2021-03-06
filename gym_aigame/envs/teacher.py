import pickle
import gym
from gym import Wrapper

class Teacher(Wrapper):
    def __init__(self, env):
        super(Teacher, self).__init__(env)

    def _close(self):
        super(Teacher, self)._close()

    def _reset(self, **kwargs):
        """
        Called at the start of an episode
        """

        obs = self.env.reset(**kwargs)

        if not isinstance(obs, dict):
            obs = { "image": obs, 'mission':'' }

        obs["advice"] = "open the first door"

        return obs

    def _step(self, action):
        """
        Called at every action
        """

        obs, reward, done, info = self.env.step(action)

        if self.env.agentPos[0] < 5:
            advice = "go right"
        else:
            advice = "get to the goal!"

        if not isinstance(obs, dict):
            obs = { "image": obs, 'mission': '' }

        obs["advice"] = advice

        return obs, reward, done, info
