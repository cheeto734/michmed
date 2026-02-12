import math


def BSA(height, weight):
   """
   height in cm
   weight in kg
   """
   return math.sqrt((height * weight) / 3600.)


def IBW(height, sex):
   """
   height in cm
   weight in kg
   sex = male or female
   """
   #convert to inches
   height = height * 0.3937008
   above_5ft = max(height - 60, 0)
  
   ibw = above_5ft * 2.3
  
   if sex == "male":
       return ibw + 50
  
   else:
       return ibw + 45.5


def adj_BW(actualBW, idealBW):
   '''
   weight in kg
   '''
   return (0.4 * (actualBW - idealBW) + idealBW)


def adj_BSA(height, weight):
   '''
   weight in kg
   '''
   return math.sqrt((height * weight) / 3600.)
