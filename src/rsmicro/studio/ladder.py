from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsLineItem, QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsScene

class LadderScene(QGraphicsScene):
 """Structured rail/wire/instruction rendering; execution remains in rsmcore."""
 def load_routine(self,routine):
  self.clear(); y=40
  left,right=60,900
  self.addLine(left,10,left,max(100,len(routine.rungs)*120),QPen(Qt.GlobalColor.black,3))
  self.addLine(right,10,right,max(100,len(routine.rungs)*120),QPen(Qt.GlobalColor.black,3))
  for number,rung in enumerate(routine.rungs,1):
   self.addSimpleText(str(number)).setPos(10,y); self.addSimpleText(rung.comment).setPos(60,y-25)
   x=80; self.addLine(left,y,x,y)
   for node in rung.nodes:
    group=QGraphicsItemGroup(); box=QGraphicsRectItem(QRectF(x,y-18,115,40)); group.addToGroup(box)
    mnemonic=getattr(node,"mnemonic",node.__class__.__name__.upper())
    label=QGraphicsSimpleTextItem(mnemonic); label.setPos(x+8,y-13); group.addToGroup(label); self.addItem(group)
    self.addLine(x+115,y,x+135,y); x+=135
   self.addLine(x,y,right,y); y+=110
