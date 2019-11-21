import random
from enum import Enum
import numpy as np
from collections import Counter

class Individual:
    def __init__(self, dim, bounds, id):
        self.ofv = 0
        self.id = id
        self.features = [random.uniform(bounds[x][0], bounds[x][1]) for x in range(dim)]

    def __repr__(self):
        return str(self.__dict__)

# simple test function
class Sphere:
    def __init__(self, dim):
        self.bounds = [[-100, 100] for x in range(dim)]

    def evaluate(self, x):
        sum = 0
        for i in range(len(x)):
            sum += x[i]**2
        return sum
        
##############################################################################    
class SOMA_Strategy(Enum):
    AllToOne, AllToAll, AllToRandom = range(3)

class ESP_SOMA:
    
    def __init__(self, dim, maxFEs, OF, NP, gap, pathLength, step, adaptivePRT):
        self.dim = dim
        self.maxFEs = maxFEs # dim * 10 000
        self.OF = OF
        self.NP = NP #100
        self.gap = gap #20
        self.adaptivePRT = adaptivePRT # true for adaptive prt
        self.pathLength = pathLength #3.0
        self.step = step #0.11
        
        self.P = None
        self.PRT = None
        self.Strategy = None
        self.Counter = None
    
    def pickBest(self, pop):
        best = None
        for i in range(len(pop)):
            if best == None or pop[i].ofv <= best.ofv:
                best = pop[i]
        return best        
        
    def pickRandom(self, pop, x):
        popCopy = pop[:]
        popCopy.remove(x)
        return random.choice(popCopy)
    
    def generatePRT(self, prt):
        array = list(range(self.dim))
        for i in range(self.dim):
            if random.uniform(0, 1) < prt:
                array[i] = 1
            else:
                array[i] = 0
        array[random.randint(0, self.dim - 1)] = 1        
        return array
    
    def bound_constrain(self, u, original):
        for i in range(self.dim):
            if u[i] < self.OF.bounds[i][0]:
                u[i] = (self.OF.bounds[i][0] + original[i]) / 2
            elif u[i] > self.OF.bounds[i][1]:
                u[i] = (self.OF.bounds[i][1] + original[i]) / 2

        return u    
    
    def roulettePRT(self):
        if self.adaptivePRT == 0:
            return 0.3
        c = Counter(self.PRT)
        #fix possible missing PRT values
        c.update(Counter([0.1, 0.3, 0.5, 0.7, 0.9]))
        mmax = sum(c.values())
        pick = random.uniform(0, mmax)
        current = 0
        for key, value in c.items():
            current += value
            if current > pick:
                return key
        return 0.3
    
    def rouletteStrategy(self):
        c = Counter(self.Strategy)
        #fix possible missing Strategies
        c.update(Counter(list(SOMA_Strategy)))
        mmax = sum(c.values())
        pick = random.uniform(0, mmax)
        current = 0
        for key, value in c.items():
            current += value
            if current > pick:
                return key
    
    # x = xi
    # xL = one Leader
    # t = actual step size
    # prt = actual generated prt vector
    def migration(self, x, xL, t, prt):
        y = list(range(self.dim))
        
        for j in range(self.dim):
            y[j] = x[j] + (xL[j] - x[j]) * t * prt[j] 
        
        return y
    
    def run(self):

        #initialization 
        fes = 0
        best = None
        
        #assign prt to population
        #assign strategy to population
        #assign counter to population
        self.PRT = list(range(self.NP))
        self.Strategy = list(range(self.NP))
        self.Counter = list(range(self.NP))
        for i in range(self.NP):
            if self.adaptivePRT == 0:
                self.PRT[i] = 0.3
            else:
                self.PRT[i] = random.choice([0.1, 0.3, 0.5, 0.7, 0.9])
        
            
            self.Strategy[i] = random.choice(list(SOMA_Strategy))
            self.Counter[i] = 0
        
        #population initialization
        id = 0
        self.P = [Individual(self.dim, self.OF.bounds, id) for x in range(self.NP)]
        for ind in self.P:
            ind.ofv = self.OF.evaluate(ind.features)
            ind.id = id
            id += 1
            fes += 1
            if best == None or ind.ofv <= best.ofv:
                best = ind
        
        #maxfes exhaustion
        while fes < self.maxFEs:
            
            newPop = []
            
            #generation iterator
            for i in range(self.NP):
                
                ind = None
                
                #pick Leader(s)
                if self.Strategy[i] == SOMA_Strategy.AllToOne:
                    xLeader = self.pickBest(self.P)
                    if xLeader == self.P[i]:
                        xLeader = []
                    else:
                        xLeader = [xLeader]
                elif self.Strategy[i] == SOMA_Strategy.AllToRandom:
                    xLeader = [self.pickRandom(self.P, self.P[i])]
                else:
                    xLeader = self.P[:]
                    xLeader.remove(self.P[i])
                
                #steps
                for t in np.arange(self.step, self.pathLength, self.step):
                    
                    prtVector = self.generatePRT(self.PRT[i])
                    #migration over leaders
                    for xL in xLeader:
                
                        y = self.migration(self.P[i].features, xL.features, t, prtVector)
                
                        #bound constraining
                        y = self.bound_constrain(y, self.P[i].features)

                        #evaluation
                        newInd = Individual(self.dim, self.OF.bounds, self.P[i].id)
                        newInd.features = y
                        newInd.ofv = self.OF.evaluate(y)   
                        fes += 1
                
                        #memory best drawn individual
                        if ind == None or ind.ofv >= newInd.ofv:
                            ind = newInd
                
                        if newInd.ofv <= best.ofv:
                            best = newInd    
                            
                        if fes >= self.maxFEs:
                            return best    
                
                
                if ind == None:
                    ind = self.P[i]
                    
                if ind.ofv >= self.P[i].ofv:
                    self.Counter[i] += 1
                    if self.Counter[i] >= self.gap:
                        self.Counter[i] = 0
                        #roulete selections
                        self.PRT[i] = self.roulettePRT()
                        self.Strategy[i] = self.rouletteStrategy()
                    
                newPop.append(ind)
            
            self.P = newPop
                    
        
        return best


        
        
dim = 10 #dimension size
NP = 100 #population size
maxFEs = 10000 * dim #maximum number of objective function evaluations
gap = 2
adaptivePRT = 1
pathLength = 3.0
step = 0.11

sphere = Sphere(dim) #defined test function
soma = ESP_SOMA(dim, maxFEs, sphere, NP, gap, pathLength, step, adaptivePRT)
resp = soma.run()
print(resp)
