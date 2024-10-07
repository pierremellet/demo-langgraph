CREATE TABLE Client (
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    account_number VARCHAR(34) PRIMARY KEY NOT NULL -- IBAN format with max length of 34 characters
);

CREATE TABLE AccountTransaction (
    account_number VARCHAR(34) NOT NULL,
    transaction_date TIMESTAMP WITH TIME ZONE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL CHECK (category IN ('TAXES', 'ENERGY', 'RESTAURANT', 'CLOTHES', 'SALARY', 'HOBBY')),
    label VARCHAR(255) NOT NULL,
    FOREIGN KEY (account_number) REFERENCES Client(account_number)
);
