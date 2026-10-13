# Memo de banderas rojas — cuarto de datos

- Fecha de corte: 2026-10-13 (horizonte de vencimientos: 12 meses)
- Modelo: claude-opus-5-5 (respuestas grabadas, sin llamar a la API)
- Documentos en la carpeta: 6

> Apoyo a la decisión. Cada dato trae documento, página y cita literal; lo que no se pudo citar
> no se reporta. No es opinión legal, inspección física, ambiental, valuación ni capacidad eléctrica.

## Banderas rojas (5)

### Severidad alta (4)

- **contrato_vence_pronto** — Inquilino Ficticio Alfa, S.A. de C.V.: el contrato vence el 2027-03-31, dentro de 12 meses desde 2026-10-13.
  - contrato_nave_1.pdf, p. 1: «vence el 31 de marzo de 2027»
- **inquilino_sin_contrato** — Inquilino Ficticio Gamma, S.A. de C.V. aparece en la relación de rentas y no hay contrato suyo leído en el cuarto de datos.
  - relacion_rentas.pdf, p. 1: «Inquilino Ficticio Gamma, S.A. de C.V. - Nave 3»
- **permiso_vencido** — LICENCIA DE USO DE SUELO: vigente solo hasta el 2025-06-30; vencido a la fecha de corte 2026-10-13.
  - permisos.pdf, p. 1: «Esta licencia es vigente hasta el 30 de junio de 2025.»
- **superficie_no_cuadra** — Nave 2: los contratos rentan 9,200.00 m² y la escritura dice 8,500.00 m² construidos (se renta más de lo que la escritura ampara).
  - escritura_parque.pdf, p. 1: «Nave 2 con una superficie construida de 8,500 m².»
  - contrato_nave_2.pdf, p. 1: «La Nave 2 tiene una superficie rentable de 9,200 m² de construcción.»

### Severidad media (1)

- **contrato_sin_garantia** — Inquilino Ficticio Beta, S.A. de C.V.: no se localizó depósito en garantía, fianza ni carta de crédito.
  - contrato_nave_2.pdf, p. 1: «la otra Inquilino Ficticio Beta, S.A. de C.V. (en lo sucesivo, el Arrendatario)»
  - contrato_nave_2.pdf: no se localizó en las 2 página(s) leídas

## Lo que dicen los oficios de suministro

- Según el oficio (oficio_suministro.pdf, p. 1): «Emisor: Suministrador Eléctrico Ficticio, en el lugar de la empresa suministradora.»
- Según el oficio (oficio_suministro.pdf, p. 1): «el servicio solicitado se atenderá en media tensión, tarifa GDMTH.»
- Según el oficio (oficio_suministro.pdf, p. 1): «La carga solicitada de 1,500 kW queda sujeta a la ejecución de obras de refuerzo en la red por cuenta del solicitante.»
- Según el oficio (oficio_suministro.pdf, p. 1): «Fecha: 3 de febrero de 2026.»

Transcripción del papel. DGED no afirma capacidad eléctrica ni megawatts (D-003).

## Documentos leídos

| Documento | Tipo | Páginas | Valores verificados | Descartados |
|---|---|---|---|---|
| contrato_nave_1.pdf | contrato_renta | 2 | 14 | 1 |
| contrato_nave_2.pdf | contrato_renta | 2 | 14 | 0 |
| escritura_parque.pdf | escritura | 1 | 10 | 0 |
| oficio_suministro.pdf | oficio_cfe | 1 | 4 | 0 |
| permisos.pdf | permiso | 2 | 11 | 0 |
| relacion_rentas.pdf | lista_rentas | 1 | 15 | 0 |

## Lo que no se revisó

- Valores propuestos por el modelo y descartados (no entran a ningún cruce):
  - contrato_nave_1.pdf · seguro: "Arrendatario paga todos los seguros" — la cita no aparece literal en el texto de esa página
- Opinión legal sobre validez, exigibilidad o firmas de los contratos.
- Superficies contra catastro o contra levantamiento físico: solo se cruzó escritura contra contrato.
- Gravámenes contra el Registro Público de la Propiedad: solo se transcribe lo que la escritura menciona.
- Anexos, convenios modificatorios y cartas laterales que no venían en la carpeta.
- Inspección física (ASTM E2018), ambiental fase I (ASTM E1527) y valuación.
- Capacidad eléctrica: de un oficio de suministro solo se transcribe lo que dice el papel (D-003).
- Renta contra mercado, conversión de moneda y recálculo de incrementos.
