"""Archived source regression; run: python radar2/test_marked_program.py."""
from datetime import date
from marked_program import parse,shape
raw="EL FINDE PASA POR LA ESTACIÓN\n\nUn line up que se renueva cada fin de semana.\n\nUna programación que se construye entre todos: la Estación, las comunidades que la habitan, los artistas  y el barrio. Muchas propuestas gratuitas y muchas cosas pasando.\n\nUn festival todos los findes de semana 🔥\n\n📆 Viernes 13\n✅  Inauguración\nMUSEO DE FOTOGRAFÍA Y ARCHIVO DE MERIDIANO V\nExposición de Víctor Bugge tresalcubo.estudio  maninofotografo \n🕐 19.00 hs.\n📍 Planta Alta\n\n✅ laferiadelplayon \n🕐 Desde las 19.00 hs. \nFeria de artesanos y emprendedores. Una feria de barrio, de arte, de trabajo, de diseño. \n📍 Playón\n\n✅  SUBSUELO +  FÁBRIACA PLANTA 5\nSUBSUELO llega con una obra de danza tango.\nFÁBRICA – PLANTA 5 propone una experiencia inmersiva de ensamble rítmico en vivo.\nfabrica.planta5  subsuelo.tango  estoesfabrica  __lunamor_na \n🕐 21.00 hs.\n📍 Playón\nGratis\n\n📆 Sábado 14\n✅ FERIA DEL PLAYÓN \n🕐 Desde las 16.00 hs. \nFeria de artesanos y emprendedores. Una feria de barrio, de arte, de trabajo, de diseño. \n📍 Playón\n\n✅  facundotorresan.oficial y su grupo entrerrianía\nMúsica litoraleña\n🕐 18.00 hs.\n📍 Playón\nGratis\n\n✅ MUSEOS A LA LUZ DE LA LUNA\n🕐 19.00 hs.\n📍 Planta Alta\n\n✅ MÁS ALLÁ DEL PIXEL\n2da Edición – Muestra de Alumnos de Photoshop\nProfesora Sabrina Morgante\n🕐 19.00 hs.\n📍 Planta Alta\n\n✅  ELVIS VIVE en la voz de John McInerny\nTributo al rey elvis_vive.john_mcinerny \n🕐 19.30 hs.\n📍 Playón\nGratis\n\n✅  NOCHE DE JAZZ\n🕐 21.00 hs.\n📍 Playón\nGratis\n\n📆 Domingo 15\n✅ FERIA DE COLECCIONES Y ANTIGÜEDADES\nsupercolecciones.oficial \n🕐 Desde las 12.00 hs. \n📍 Playón\n\n✅ FERIA DEL PLAYÓN \n🕐 Desde las 14.00 hs. \nFeria de artesanos y emprendedores. Una feria de barrio, de arte, de trabajo, de diseño. \n📍 Playón\n\n✅  PERRO ANDALUZ seru.perroandaluz \nLa Música de Seru Girán\n🕐 17.00 hs.\n📍 Playón\nGratis\n\n✅  versionanimaloficial \nHomenaje a Soda Stereo \n🕐 18.30 hs.\n📍 Playón\nGratis\n\n✅  CLASE ABIERTA DE SWING swingoutstudiolp \n🕐 18.00 hs. \n📍 Planta Alta\nGratis\n\n17 y 71 · Meridiano V\nLa Plata."
base=date(2026,11,11)
rows=parse(raw,base)
assert shape(raw) and len(rows)==14
assert [sum(x['date'].day==d for x in rows) for d in (13,14,15)]==[3,6,5]
assert rows[0]['title'].startswith('MUSEO DE FOTOGRAFÍA') and rows[0]['time']=='19:00'
assert rows[-1]['time']=='18:00' and rows[-1]['sector']=='Planta Alta'
assert len([x for x in rows if x['date'].day==14 and x['time']=='19:00'])==2
assert parse(raw.replace('Sábado 14','Sábado 15'),base)==[]
assert parse(raw,None)==[]
assert parse(raw.replace('📆 Domingo 15','📆 Viernes 13'),base)==[]
assert parse(raw.replace('🕐 19.00 hs.','🕐 19.00 hs. y 22.00 hs.',1),base)[0]['time'] is None
assert parse(raw.replace('🕐 19.00 hs.','🕐 00.00 hs.',1),base)[0]['time'] is None
cross='📆 Sábado 31\n✅ Aventura\n10 hs\n📍 Patio\n📆 Domingo 1\n✅ Otra actividad\n11 hs\n📍 Patio'
assert [x['date'].isoformat() for x in parse(cross,date(2026,10,30))]==['2026-10-31','2026-11-01']
print('PASS marked program: 14 scoped claims, cross-month, date/clock guards')
