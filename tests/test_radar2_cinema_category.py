"""Cinema labels with explicit series names; negative controls avoid genre guesses."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'radar2'))
from extract import category


class CinemaCategoryRegression(unittest.TestCase):
 def test_explicit_local_series(self):
  for value in (
   "Cine Select: El origen de los guardianes",
   "Cine Select: Nené y las cosas",
   "Cine EcoSelect: El increíble castillo vagabundo",
   "Cine EcoSelect: Sorcerer",
   "Cine EcoSelect - Pertenencias",
  ):
   with self.subTest(value=value):
    self.assertEqual(category(value),"Cine")

 def test_not_assume_cinema_from_unrelated_context(self):
  for value in (
   "Cine Select presentará su temporada anual",
   "Bingo musical de Veto y Fer",
   "Feria del Playón",
   "Taller de cine experimental",
  ):
   with self.subTest(value=value):
    self.assertNotEqual(category(value),"Cine")

 def test_not_override_existing_domain_rules(self):
  self.assertEqual(category("Concierto de Diego Frenkel"),"Música")
  self.assertEqual(category("Cata de vinos naturales"),"Vino")
  self.assertEqual(category("Una obra de teatro"),"Teatro")


if __name__=='__main__':
 unittest.main()
