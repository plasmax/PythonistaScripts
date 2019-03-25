'''
Make a cube that rotates when you tap+drag to understand the basics of defining a 3D shape an manipulating tbe positions. Eventually describe a 3D node graph.
'''
import time
from math import *
from scene import *

square_2d = [
  (0,0),
  (0,1),
  (1,1),
  (1,0)
]

square_3d = [
  (0,0,0),
  (0,1,0),
  (1,1,0),
  (1,0,0),
  (0,0,1),
  (0,1,1),
  (1,1,1),
  (1,0,1),
]

def angle(p1,p2):
  '''Return angle in radians between pts'''
  x1,y1,x2,y2 = (*p1,*p2)
  dx,dy = x1-x2, y1-y2
  return atan2(dx,dy)
  hyp = hypot(dx,dy)
  rads = asin((sin(radians(90))/hyp)*dy)
  return rads
  #print(degrees(rads))

class Graph(Scene):
  pts = []
  def setup(self):
    self.last_time = None
    scale = 200
    cx,cy = self.size/2
    self.centre = (cx,cy)
    for x,y in square_2d:
      pt = SpriteNode(size=(10,10))
      px = (x*scale)+cx-(scale/2)
      py = (y*scale)+cy-(scale/2)
      pt.position = (px,py)
      self.pts.append(pt)
      self.add_child(pt)
      
  def touch_began(self, touch):
    pass
    
  def touch_moved(self, touch):
    self.rotate_2d(touch.location)
    self.calc_vel(touch)
    
  def touch_ended(self, touch):
    self.drift_to_a_halt()
    
  def drift_to_a_halt(self):
    #print(self.vel)
    a = radians(
      degrees(self.last_angle*self.vel)
    )
    co,si = cos(a),sin(a)
    cx,cy = c = self.centre
    for pt in self.pts:
      x,y = pt.position
      ox,oy = x-cx,y-cy
      x1 = (ox*co-oy*si)+cx
      y1 = (oy*co+ox*si)+cy
      #pt.remove_all_actions()
      move = Action.move_to(
        x1, y1, 1, TIMING_SINODIAL
      )
      pt.run_action(move)
  
  def rotate_2d(self, loc):
    tx,ty = t = loc
    cx,cy = c = self.centre
    
    # calc angle between loc
    # and first pt in array
    # ---------------------------
    r = angle(c,t)
    pt = self.pts[0]
    p = pt.position
    a = angle(c,p)-r
    co,si = cos(a),sin(a)
    
    # move each pt in array by angle
    # ---------------------------
    for pt in self.pts:
      x,y = pt.position
      
      # offset to lower left corner
      ox,oy = x-cx,y-cy
      
      # calc new pos from angle
      x1 = (ox*co-oy*si)+cx
      y1 = (oy*co+ox*si)+cy
      
      # do the move
      move = Action.move_to(
        x1, y1, 0, TIMING_SINODIAL
      )
      pt.run_action(move)
    self.last_angle = a
  	
  def calc_vel(self,touch):
    tx,ty = t = touch.location
    # ---------------------------
    # velocity 
    px,py = tp = touch.prev_location
    start = time.time()
    if self.last_time is None:
      self.vel = 0
    else:
      self.vel = sqrt(
        (abs(tx-px)**2)+(abs(ty-py)**2)
      )/(self.last_time/start)
    self.last_time = start
    # ---------------------------
    

    
run(Graph())


