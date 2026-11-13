-- SIMTELE-RISK · esquema PostgreSQL (Supabase / Neon)
-- Ejecutar completo en el SQL Editor (se puede correr más de una vez).

CREATE TABLE IF NOT EXISTS caso_estudio (
	id SERIAL NOT NULL, 
	nombre VARCHAR(60) NOT NULL, 
	modelo_version VARCHAR(20) DEFAULT '1.0' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);

CREATE TABLE IF NOT EXISTS escenario (
	id SERIAL NOT NULL, 
	caso_id INTEGER NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	parametros_json JSONB NOT NULL, 
	fuente_datos TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_escenario_tipo CHECK (tipo IN ('NORMAL','ESTRÉS','MAL_CONDICIONADO')), 
	FOREIGN KEY(caso_id) REFERENCES caso_estudio (id)
);

CREATE TABLE IF NOT EXISTS simulacion (
	id SERIAL NOT NULL, 
	escenario_id INTEGER NOT NULL, 
	fecha TIMESTAMP WITH TIME ZONE NOT NULL, 
	equipo VARCHAR(80), 
	estado VARCHAR(20) DEFAULT 'COMPLETADA' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(escenario_id) REFERENCES escenario (id)
);

CREATE TABLE IF NOT EXISTS ejecucion_metodo (
	id SERIAL NOT NULL, 
	simulacion_id INTEGER NOT NULL, 
	metodo VARCHAR(60) NOT NULL, 
	tolerancia FLOAT, 
	paso FLOAT, 
	max_iter INTEGER, 
	convergio BOOLEAN NOT NULL, 
	tiempo_ms FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(simulacion_id) REFERENCES simulacion (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS iteracion_resultado (
	id SERIAL NOT NULL, 
	ejecucion_id INTEGER NOT NULL, 
	numero INTEGER NOT NULL, 
	aproximacion_json JSONB, 
	residual FLOAT, 
	error_abs FLOAT, 
	error_rel FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ejecucion_id) REFERENCES ejecucion_metodo (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resultado_resumen (
	id SERIAL NOT NULL, 
	ejecucion_id INTEGER NOT NULL, 
	referencia TEXT, 
	valor_json JSONB, 
	metrica_error_json JSONB, 
	interpretacion TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ejecucion_id) REFERENCES ejecucion_metodo (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_simulacion_escenario ON simulacion(escenario_id);
CREATE INDEX IF NOT EXISTS ix_ejecucion_sim ON ejecucion_metodo(simulacion_id);
CREATE INDEX IF NOT EXISTS ix_iteracion_ej ON iteracion_resultado(ejecucion_id, numero);

-- Datos iniciales: los 4 casos de estudio
INSERT INTO caso_estudio (nombre, modelo_version) VALUES
  ('Detención de emergencia', '1.0'),
  ('Deterioro y mantenimiento', '1.0'),
  ('Oscilaciones por viento', '1.0'),
  ('Reconstrucción de sensores', '1.0')
ON CONFLICT (nombre) DO NOTHING;
