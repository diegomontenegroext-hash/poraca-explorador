"""C4: exact archived public detail shapes; pure parser and no network."""
import pathlib,sys,unittest
from datetime import date
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'radar2'))
from extract import linked_program_rows
NOW=date(2026,11,13)
METHOD='public_linked_cultural_detail_v1'
def film(title,director,when,venue,kind='Largometrajes'):
 url='https://fesaalp.com/peliculas/test-film/'
 return dict(url=url,final_url=url,http_status=200,source='FESAALP',title=title+' | FESAALP',
  text='Descargá la grilla # Volver Competencia '+kind+' '+title+' De '+director+' '+when+' - '+venue+' Guardar en calendario Sinopsis Ficha Año 2025')
class LinkedProgram(unittest.TestCase):
 def test_real_feature_rows(self):
  cases=[
   ('La mancha','Ramiro García Bogliano, Adrián Garcia Bogliano','Sábado 21/11 - 21:30 h','Cine Select','2026-11-21','21:30','Cine Select'),
   ('Barrio triste','Stillz','Domingo 22/11 - 20:00 h','CC Malvinas','2026-11-22','20:00','Centro Cultural Islas Malvinas'),
   ('A veces me entra tristeza, otras veces rebelión','María Aparicio','Martes 24/11 - 19:30 h','Cine Select','2026-11-24','19:30','Cine Select'),
   ('El Fantasma','Ignacio Masllorens, David Lamelas','Miércoles 25/11 - 21:30 h','Cine Select','2026-11-25','21:30','Cine Select'),
   ('Familia teme enfrentar una nueva noche de terror','Cristian Ponce','Jueves 26/11 - 21:30 h','Cine Select','2026-11-26','21:30','Cine Select'),
   ('Funk','Aly Muritiba','Domingo 22/11 - 21:00 h','Pasaje Dardo Rocha (Sala B)','2026-11-22','21:00','Pasaje Dardo Rocha (Sala B)'),
   ('Los días libres','Lucila Mariani','Domingo 22/11 - 19:30 h','Cine Municipal Select Espacio INCAA','2026-11-22','19:30','Cine Select'),
   ('Pedro en el país','María Alché, Benjamín Naishtat','Miércoles 25/11 - 20:00 h','Cine Select','2026-11-25','20:00','Cine Select')]
  for title,director,when,venue,day,time,place in cases:
   d=film(title,director,when,venue)
   r=linked_program_rows(d,METHOD,NOW)
   self.assertEqual(len(r),1,title);self.assertEqual((r[0]['title'],r[0]['date'],r[0]['time'],r[0]['venue']),(title,day,time,place))
   self.assertIn(r[0]['block'],d['text'])
 def test_negative(self):
  d=film('Para los contrincantes','Federico Luis','Domingo 22/11 - 18:00 h','Islas Malvinas','Cortometrajes Ficción')
  self.assertEqual(linked_program_rows(d,METHOD,NOW),[])
  d=film('Funk','Aly Muritiba','Lunes 22/11 - 21:00 h','Cine Select')
  self.assertEqual(linked_program_rows(d,METHOD,NOW),[])
  d=film('Funk','Aly Muritiba','Domingo 22/11 - 21:00 h','Sala desconocida')
  self.assertEqual(linked_program_rows(d,METHOD,NOW),[])
  d=film('Funk','Aly Muritiba','Domingo 22/11 - 21:00 h','Cine Select');d['final_url']='https://other.example/'
  self.assertIsNone(linked_program_rows(d,METHOD,NOW))
 def test_dynamo(self):
  url='https://www.dynamoteatro.com/event/170750-agridulce-expres'
  d=dict(url=url,final_url=url,http_status=200,source='Dynamo Teatro',title='Agridulce Expres | Dynamo Teatro',
   text='Agridulce Expres Dynamo Teatro C. 17 1754, esquina 68, B1900 La Plata, Provincia de Buenos Aires, Argentina Funciones Domingo 22 de noviembre — 20:00 hs Viernes 27 de noviembre — 21:00 hs Lugar: Dynamo Teatro From $24.000,00 Buy')
  self.assertEqual([(r['date'],r['time']) for r in linked_program_rows(d,METHOD,NOW)],[('2026-11-22','20:00'),('2026-11-27','21:00')])
  d['text']=d['text'].replace('Viernes 27 de noviembre — 21:00 hs','Viernes 27 de noviembre')
  self.assertEqual(linked_program_rows(d,METHOD,NOW),[])
if __name__=='__main__':unittest.main()
