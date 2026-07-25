from collections import deque
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter,QPen
from PySide6.QtWidgets import QLabel,QPushButton,QDoubleSpinBox,QProgressBar,QWidget

class LiveLabel(QLabel):
 def update_value(self,value,quality="GOOD",forced=False):
  suffix="" if quality=="GOOD" else f" [{quality}]"
  if forced: suffix+=" [FORCED]"
  self.setText(f"{value}{suffix}"); self.setAccessibleName(f"value {value}, quality {quality}"+(" forced" if forced else ""))
class BooleanIndicator(LiveLabel):
 def update_value(self,value,quality="GOOD",forced=False): super().update_value("Running" if value else "Stopped",quality,forced)
class OperatorButton(QPushButton):
 writeRequested=Signal(object)
 def __init__(self,text,action,parent=None): super().__init__(text,parent); self.action=action; self.pressed.connect(self._press); self.released.connect(self._release)
 def _press(self): self.setText(self.text()+" (pending)"); self.writeRequested.emit(self.action.get("value",True))
 def _release(self):
  if self.action.get("type")=="MOMENTARY": self.writeRequested.emit(self.action.get("release_value",False))
class NumericInput(QDoubleSpinBox):
 writeRequested=Signal(object)
 def commit(self): self.writeRequested.emit(self.value())
class TrendWidget(QWidget):
 def __init__(self,parent=None,maximum_points=1000): super().__init__(parent); self.points=deque(maxlen=maximum_points)
 def add_point(self,timestamp,value,quality="GOOD",forced=False): self.points.append((timestamp,float(value),quality,forced)); self.update()
 def paintEvent(self,event):
  p=QPainter(self); p.drawText(8,18,"Trend — bounded samples")
  good=[x for x in self.points if x[2]=="GOOD"]
  if len(good)>1:
   values=[x[1] for x in good]; lo,hi=min(values),max(values); span=hi-lo or 1
   for i in range(1,len(good)):
    x1=(i-1)*self.width()/(len(good)-1); x2=i*self.width()/(len(good)-1)
    y1=self.height()-(good[i-1][1]-lo)/span*(self.height()-25); y2=self.height()-(good[i][1]-lo)/span*(self.height()-25); p.drawLine(int(x1),int(y1),int(x2),int(y2))

def create_widget(obj):
 t=obj.type; props=obj.properties
 if t=="label": return QLabel(props.get("text","Label"))
 if t=="boolean_indicator": return BooleanIndicator("Unavailable")
 if t in {"pushbutton","navigation_button"}: return OperatorButton(props.get("text","Command"),obj.action)
 if t=="numeric_input": return NumericInput()
 if t=="bar": return QProgressBar()
 if t=="trend": return TrendWidget(maximum_points=int(props.get("maximum_points",1000)))
 return LiveLabel(t.replace("_"," ").title()+" — unavailable")
