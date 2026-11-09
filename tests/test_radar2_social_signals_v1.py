import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'radar2'))
from collector import TARGETED_EVENT_SIGNALS
from extract import category
class SocialSignals(unittest.TestCase):
 def test_targets(self):
  for s in ['Tribu running social','La Plata Pedalea bicicleteada',
   'Los Paralelos salida ciclismo','Experiencia Kayak remada',
   'Encuentro de rollers','Caminata grupal','Senderismo en el bosque','Stand up paddle']:
   self.assertTrue(TARGETED_EVENT_SIGNALS.search(s),s)
  for s in ['Gimnasio pesas','Café sin programa','Stand up humor']:
   self.assertFalse(TARGETED_EVENT_SIGNALS.search(s),s)
 def test_category(self):
  self.assertEqual(category('Tolosa Corre 2026 carrera solidaria'),'Deporte')
  self.assertEqual(category('Encuentro de kayak'),'Deporte')
if __name__=='__main__':unittest.main()
