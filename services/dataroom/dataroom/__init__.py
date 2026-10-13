"""Lector del cuarto de datos de DGED Systems (MVP, D-013).

Lee una carpeta de PDF (contratos de renta, escrituras, permisos, oficios de
suministro), extrae con Claude un esquema fijo por tipo de documento y solo deja
pasar los valores cuya cita aparece literal en la página que dicen. Los cruces
entre documentos los hace el código, no el modelo. Ver docs/14-lector-dataroom.md.
"""
