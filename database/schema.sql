CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE clients (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name  varchar(50) NOT NULL,
    last_name   varchar(50),
    phone       varchar(20) NOT NULL UNIQUE,
    email       varchar(100),
    notes       text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE masters (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_name  varchar(50) NOT NULL,
    last_name   varchar(50),
    phone       varchar(20),
    is_active   boolean NOT NULL DEFAULT true,
    hired_at    date NOT NULL DEFAULT current_date
);

CREATE TABLE service_categories (
    id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name  varchar(100) NOT NULL UNIQUE
);

CREATE TABLE services (
    id                integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id       integer       NOT NULL REFERENCES service_categories(id),
    name              varchar(100)  NOT NULL,
    price             numeric(10,2) NOT NULL CHECK (price >= 0),
    duration_minutes  integer       NOT NULL CHECK (duration_minutes > 0),
    is_active         boolean       NOT NULL DEFAULT true,
    UNIQUE (category_id, name)
);

CREATE TABLE master_services (
    master_id   integer NOT NULL REFERENCES masters(id)  ON DELETE CASCADE,
    service_id  integer NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    PRIMARY KEY (master_id, service_id)
);

CREATE TABLE users (
    id             integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username       varchar(50) NOT NULL UNIQUE,
    password_hash  text        NOT NULL,
    role           varchar(10) NOT NULL CHECK (role IN ('admin', 'master')),
    master_id      integer     REFERENCES masters(id),
    is_active      boolean     NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CHECK (
        (role = 'master' AND master_id IS NOT NULL) OR
        (role = 'admin'  AND master_id IS NULL)
    )
);

CREATE TABLE appointments (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id   integer     NOT NULL REFERENCES clients(id),
    master_id   integer     NOT NULL REFERENCES masters(id),
    start_time  timestamptz NOT NULL,
    end_time    timestamptz NOT NULL,
    status      varchar(15) NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show')),
    comment     text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CHECK (end_time > start_time),
    CONSTRAINT no_overlapping_appointments
        EXCLUDE USING gist (
            master_id WITH =,
            tstzrange(start_time, end_time) WITH &&
        ) WHERE (status IN ('scheduled', 'completed'))
);

CREATE TABLE appointment_services (
    appointment_id    integer       NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    service_id        integer       NOT NULL REFERENCES services(id),
    price_at_booking  numeric(10,2) NOT NULL CHECK (price_at_booking >= 0),
    PRIMARY KEY (appointment_id, service_id)
);

CREATE TABLE master_schedules (
    id          integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    master_id   integer  NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    weekday     smallint NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    start_time  time     NOT NULL,
    end_time    time     NOT NULL,
    CHECK (end_time > start_time),
    UNIQUE (master_id, weekday)
);

CREATE TABLE payments (
    id              integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    appointment_id  integer       NOT NULL REFERENCES appointments(id),
    amount          numeric(10,2) NOT NULL CHECK (amount > 0),
    method          varchar(10)   NOT NULL CHECK (method IN ('cash', 'card', 'transfer')),
    paid_at         timestamptz   NOT NULL DEFAULT now(),
    created_by      integer       REFERENCES users(id)
);

CREATE INDEX idx_services_category        ON services(category_id);
CREATE INDEX idx_appointments_client      ON appointments(client_id);
CREATE INDEX idx_appointments_master_time ON appointments(master_id, start_time);
CREATE INDEX idx_appointment_services_svc ON appointment_services(service_id);
CREATE INDEX idx_payments_appointment     ON payments(appointment_id);

CREATE VIEW v_appointment_balance AS
SELECT
    a.id AS appointment_id,
    a.start_time,
    a.status,
    COALESCE(s.total, 0)                       AS total_price,
    COALESCE(p.paid, 0)                        AS total_paid,
    COALESCE(s.total, 0) - COALESCE(p.paid, 0) AS balance_due
FROM appointments a
LEFT JOIN (
    SELECT appointment_id, SUM(price_at_booking) AS total
    FROM appointment_services
    GROUP BY appointment_id
) s ON s.appointment_id = a.id
LEFT JOIN (
    SELECT appointment_id, SUM(amount) AS paid
    FROM payments
    GROUP BY appointment_id
) p ON p.appointment_id = a.id;

