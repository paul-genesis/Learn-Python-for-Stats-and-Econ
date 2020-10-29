import pandas as pd
import random
import math
from randomdict import RandomDict

from Patch import *
from AgentBranch import *
#Model.py
class Model():
    def __init__(self, gui, num_agents, data_aggregator, mutate, genetic):
        self.GUI = gui
        self.data_aggregator = data_aggregator
        self.initial_population = num_agents
        self.mutate = mutate
        self.genetic = genetic
        if self.mutate:
            self.max_mutate_rate = .5
        if self.genetic:
            self.cross_over_rate = .5
        ############    set model parameters    ############
        self.total_agents_created = 0   
        self.goods = ["sugar", "water"]
        self.goods_params = {good:{"min":5,
                                   "max":25} for good in self.goods}
        
        self.max_init_demand_vals = {"price":{"min": 1/10,
                                              "max": 10},
                                     "quantity":{"min":1,
                                                 "max":100}}
        self.consumption_rate = {"sugar":.5,
                                 "water":.5}
        
        self.breeds = ["basic", "herder", "switcher", "arbitrageur"]
        basic = .5
        self.breed_probabilities = {"basic":basic, # if you are not a basic, you are a switcher
                                    "herder":.5,
                                    "arbitrageur":.5}
        self.max_vision = 1
        # record price of every transaction
        # then take average at end of period
        self.transaction_prices = []
        
        ############ import map and build nav_dict ############
        # hash table that identifies possible moves relative to agent position 
        self.nav_dict = {
            v:{
                i:{
                    j: True for j in range(-v, v + 1) if 0 < (i ** 2 + j ** 2) <= (v ** 2)}
                for i in range(-v, v + 1)}
            for v in range(1, self.max_vision + 1)}
        #sugarMap.shape calls the a tuple with dimensions
        #of the dataframe
        self.sugarMap = pd.read_csv('sugar-map.txt', header = None, sep = ' ')
        # add 1 to each max_Val
        for key in self.sugarMap:
            self.sugarMap[key] = self.sugarMap[key].add(1)
        self.rows, self.cols = self.sugarMap.shape
        
        ############   Initialization   ############ 
        self.initializePatches()
        self.initializeAgents()
        # self.aggregate_data = {"agent":}
    
    def initializePatches(self):
        #Instantiate Patches
        #Create a dictionary to hold the patches, organize as grid. 
        #We first fill these with zeros as placeh holders
        self.patch_dict = {row:{col:0}
                           for row in range(self.rows) for col in range(self.cols)}
        for row in range(self.rows):
            for col in range(self.cols):
                # replace zeros with actual Patch objects
                good = "sugar" if row + col >= self.rows else "water"
                self.patch_dict[row][col] = Patch(self,  row , col, 
                                              self.sugarMap[row][col], good)
    # use RandomDict - O(n) time complexity - for choosing random empty patch
        self.empty_patches = RandomDict({
            (row,col):self.patch_dict[row][col]
            for row in range(self.rows) for col in range(self.cols)})
        
    def initializeAgents(self):
        # agents stored in a dict by ID
        self.agent_dict = {}
        # dead agents will be removed from agent_dict
        self.dead_agent_dict = {}
        for i in range(self.initial_population):
            self.total_agents_created += 1
            ID = self.total_agents_created
            row, col = self.chooseRandomEmptyPatch()  
            self.agent_dict[ID] = Agent(self, row, col, ID)
            self.patch_dict[row][col].agent = self.agent_dict[ID]
        self.population = self.total_agents_created
#     def recordAgentLocationInDict(self, agent):
#         patchIndex = self.convert2dTo1d(agent.row, agent.col)
#         self.agentLocationDict[patchIndex] = agent

    def chooseRandomEmptyPatch(self):
        row, col = self.empty_patches.random_key() 
        del self.empty_patches[row, col]

        return row, col

    def runModel(self, periods):
        for period in range(1, periods + 1):
            self.growPatches()
            agent_list = list(self.agent_dict.values())
            random.shuffle(agent_list)
            for agent in agent_list:
                agent.move()
                agent.harvest()
                agent.trade()
                agent.consume()
                agent.reproduce()
                agent.checkAlive()
                agent.updateParams()
            self.population = len(agent_list)
            
            self.data_aggregator.collectData(self, self.GUI.name, 
                                             self.GUI.run, period)
            if period % self.GUI.every_t_frames == 0:
                self.data_aggregator.showData(self.GUI.name, self.GUI.run)
                if self.GUI.live_visual:
                    self.GUI.parent.title("Sugarscape: " + str(period))
                    self.GUI.updatePatches()
                    self.GUI.moveAgents()
                    self.GUI.canvas.update()
    
    def growPatches(self):
        for i, vals in self.patch_dict.items():
            for patch in vals.values():
                if patch.Q < patch.maxQ:
                    patch.Q += 1