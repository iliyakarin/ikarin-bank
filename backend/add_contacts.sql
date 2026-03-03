CREATE TABLE contacts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    contact_name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

CREATE INDEX ix_contacts_id ON contacts (id);
CREATE INDEX ix_contacts_user_id ON contacts (user_id);
