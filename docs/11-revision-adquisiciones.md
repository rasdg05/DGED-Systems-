# Revisión técnica de adquisiciones — banderas rojas antes de la exclusividad

Aprobado el 2026-10-12 (D-013). Para FIBRAs, fondos y desarrolladores que
compran naves o portafolios industriales.

## Cómo compra el cliente

Carta de intención → cuarto de datos → 30–60 días de exclusividad → despachos en
paralelo (legal, estado físico ASTM E2018, ambiental fase I ASTM E1527,
valuación) → banderas rojas. Los bancos exigen reportes de firmas con
ingeniero certificado y seguro de responsabilidad profesional: **ese reporte no
lo firmamos**. Llegamos antes o al lado de esas firmas, no en su lugar.

## Qué entregamos

1. **Lectura del cuarto de datos**: contratos de renta, escrituras, permisos,
   oficios. Cada dato con documento y página; lo que no está literal no se
   reporta (regla del lector de Gestor Morelos).
2. **Rent roll automático**: inquilino, m², renta, vencimiento, incrementos,
   garantías, quién paga mantenimiento, predial y seguro.
3. **Cruces**: m² de escritura vs contrato vs catastro; permisos o contratos que
   vencen dentro del horizonte de la inversión; oficios de CFE contra el uso
   declarado (lo que dice el papel, nunca capacidad: D-003).
4. **Riesgo físico por nave** con Atlas, con fuente y fecha.
5. **Memo de banderas rojas** priorizado, con cita a página y lo **no revisado**
   escrito.

## Qué no entregamos

Opinión legal, inspección física, ambiental firmado, valuación, capacidad
eléctrica certificada. Se recomienda a sus despachos o va con un socio de
ingeniería.

## Precio

Por nave, con tope por portafolio (D-013, montos en D-014): **USD 3,500 por
nave**, mínimo 3 naves (USD 10,500), **tope de USD 45,000 por memo hasta 60
naves**. Hasta 3 contratos por nave incluidos; extra, USD 150 cada uno. 50% al
recibir el cuarto de datos, 50% contra entrega; se acredita contra un Screening
firmado en 90 días. Comparables en `docs/13-comparables-precio.md` §1.

## Cómo se vende

1. Memo de muestra con un parque público y un cuarto de datos **ficticio y
   marcado como tal**.
2. Contacto directo con adquisiciones de Fibra Mty, FIBRA Prologis y Vesta
   (D-012): "Banderas rojas de su próxima adquisición en 72 horas, antes de
   firmar exclusividad. Cada dato con su página."
3. Socios: despachos legales y firmas de ingeniería que ya hacen la revisión.
4. LinkedIn: un parque o corredor público por semana, con fuentes.
5. AMPIP después del primer memo real.

## Antes de vender

- Lector del cuarto de datos (`services/dataroom/`): MVP listo sobre la muestra;
  falta medirlo con la API real.
- Instantáneas inmutables y memo PDF (semana 2 del plan).
- NDA, espacio por cliente, borrado al cierre; revisar términos comerciales de
  la API de Anthropic sobre retención antes de procesar documentos de clientes.
- Socio de ingeniería para el paquete completo.
