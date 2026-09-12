-- KisanSetu PostgreSQL schema (v1)
-- Run in DB `kisan_setu`. Requires pgcrypto or PG13+ gen_random_uuid (core).

-- ================= farmers =================
CREATE TABLE IF NOT EXISTS farmers (
    id                   BIGSERIAL PRIMARY KEY,
    farmer_uid           UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    name                 VARCHAR(255) NOT NULL,
    mobile               VARCHAR(15) NOT NULL UNIQUE,
    village              VARCHAR(100) NOT NULL,
    district             VARCHAR(100) NOT NULL,
    state                VARCHAR(100) NOT NULL,
    pincode              VARCHAR(6),
    pmkisan_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    icar_pest_risk_score NUMERIC(4,3) CHECK (icar_pest_risk_score BETWEEN 0 AND 1),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ================= users (auth; existing table maps here) =================
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('farmer','fpo','bank')),
    farmer_id     BIGINT REFERENCES farmers(id) ON DELETE CASCADE,
    fpo_id        BIGINT REFERENCES fpos(id) ON DELETE CASCADE,
    is_staff      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ================= fpos =================
CREATE TABLE IF NOT EXISTS fpos (
    id                   BIGSERIAL PRIMARY KEY,
    fpo_uid              UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    legal_name           VARCHAR(255) NOT NULL,
    reg_number           VARCHAR(100) NOT NULL UNIQUE,
    district             VARCHAR(100) NOT NULL,
    state                VARCHAR(100) NOT NULL,
    facilitation_fee_rate NUMERIC(5,4) NOT NULL DEFAULT 0.0200
                         CHECK (facilitation_fee_rate BETWEEN 0 AND 0.05),
    wallet_balance       NUMERIC(14,2) NOT NULL DEFAULT 0,
    verified             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ================= fpo_memberships =================
CREATE TABLE IF NOT EXISTS fpo_memberships (
    id                    BIGSERIAL PRIMARY KEY,
    farmer_id             BIGINT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    fpo_id                BIGINT NOT NULL REFERENCES fpos(id) ON DELETE CASCADE,
    membership_status     VARCHAR(20) NOT NULL DEFAULT 'pending'
                          CHECK (membership_status IN ('pending','active','suspended','exited')),
    member_integrity_flag BOOLEAN NOT NULL DEFAULT FALSE,
    attestor_user_id      BIGINT REFERENCES users(id),
    conflict_of_interest  BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at             TIMESTAMPTZ,
    attested_at           TIMESTAMPTZ,
    exited_at             TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_membership UNIQUE (farmer_id, fpo_id)
);

-- ================= crop_cycles =================
CREATE TABLE IF NOT EXISTS crop_cycles (
    id                    BIGSERIAL PRIMARY KEY,
    farmer_id             BIGINT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    crop_code             VARCHAR(20) NOT NULL,
    season                VARCHAR(10) NOT NULL CHECK (season IN ('Kharif','Rabi','Zaid')),
    year                  SMALLINT NOT NULL,
    acreage               NUMERIC(8,2) NOT NULL CHECK (acreage > 0),
    expected_yield_q      NUMERIC(10,2),
    nhb_yield_benchmark_q NUMERIC(10,2),
    status                VARCHAR(20) NOT NULL DEFAULT 'planned'
                          CHECK (status IN ('planned','growing','harvesting','completed','lost')),
    geotag                JSONB,
    planted_at            TIMESTAMPTZ,
    harvest_expected_at   DATE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_cycle UNIQUE (farmer_id, crop_code, season, year)
);
CREATE INDEX IF NOT EXISTS ix_crop_cycles_farmer ON crop_cycles(farmer_id);

-- ================= credit_profiles =================
CREATE TABLE IF NOT EXISTS credit_profiles (
    id                   BIGSERIAL PRIMARY KEY,
    farmer_id            BIGINT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    computed_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    safe_credit_limit    NUMERIC(14,2) NOT NULL CHECK (safe_credit_limit >= 0),
    repayment_coverage   NUMERIC(10,4),
    component_scores     JSONB NOT NULL,
    risk_haircut         NUMERIC(5,4) NOT NULL CHECK (risk_haircut BETWEEN 0 AND 1),
    credit_tier          VARCHAR(20) NOT NULL CHECK (credit_tier IN ('Low','Medium','High')),
    model_version        VARCHAR(20) NOT NULL,
    input_snapshot       JSONB NOT NULL,
    weather_loss_ratio   NUMERIC(4,3) CHECK (weather_loss_ratio BETWEEN 0 AND 1),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_farmer_latest UNIQUE (farmer_id, computed_at)
);
CREATE INDEX IF NOT EXISTS ix_credit_profiles_farmer ON credit_profiles(farmer_id, computed_at DESC);

-- ================= lenders =================
CREATE TABLE IF NOT EXISTS lenders (
    id                 BIGSERIAL PRIMARY KEY,
    legal_name         VARCHAR(255) NOT NULL UNIQUE,
    institution_class  VARCHAR(20) NOT NULL CHECK (institution_class IN ('bank','nbfc','coop')),
    region             VARCHAR(100),
    psl_target_year    SMALLINT
);

-- ================= loan_applications =================
CREATE TABLE IF NOT EXISTS loan_applications (
    id                   BIGSERIAL PRIMARY KEY,
    application_uid      UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    farmer_id            BIGINT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    fpo_id               BIGINT REFERENCES fpos(id),
    lender_id            BIGINT NOT NULL REFERENCES lenders(id),
    credit_profile_id    BIGINT NOT NULL REFERENCES credit_profiles(id),
    principal            NUMERIC(14,2) NOT NULL CHECK (principal > 0),
    tenure_months        SMALLINT NOT NULL CHECK (tenure_months BETWEEN 3 AND 60),
    annual_interest_rate NUMERIC(6,4) NOT NULL CHECK (annual_interest_rate BETWEEN 0 AND 0.30),
    origination_fee_rate NUMERIC(5,4) NOT NULL DEFAULT 0.0175
                         CHECK (origination_fee_rate BETWEEN 0.015 AND 0.020),
    status               VARCHAR(20) NOT NULL DEFAULT 'underwritten'
                         CHECK (status IN ('draft','underwritten','queued','approved',
                                           'disbursing','active','repaid','written_off')),
    psl_category         VARCHAR(40),
    psl_eligible         BOOLEAN NOT NULL DEFAULT FALSE,
    underwrite_snapshot  JSONB NOT NULL,
    decided_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_loan_apps_queue ON loan_applications(lender_id, status)
    WHERE status IN ('queued','approved');

-- ================= disbursement_tranches =================
CREATE TABLE IF NOT EXISTS disbursement_tranches (
    id                  BIGSERIAL PRIMARY KEY,
    loan_application_id BIGINT NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    tranche_no          SMALLINT NOT NULL,
    amount              NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    payee_type          VARCHAR(20) NOT NULL CHECK (payee_type IN ('vendor','farmer','escrow')),
    payee_ref           VARCHAR(100) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                        CHECK (status IN ('scheduled','released','blocked','failed','reversed')),
    release_rule        JSONB NOT NULL,
    released_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tranche UNIQUE (loan_application_id, tranche_no)
);

-- ================= data_consents =================
CREATE TABLE IF NOT EXISTS data_consents (
    id                  BIGSERIAL PRIMARY KEY,
    consent_uid         UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    farmer_id           BIGINT NOT NULL REFERENCES farmers(id) ON DELETE CASCADE,
    counterparty_type   VARCHAR(20) NOT NULL CHECK (counterparty_type IN ('lender','fpo','buyer','platform')),
    counterparty_id     BIGINT NOT NULL,
    purpose             VARCHAR(255) NOT NULL,
    consent_version     VARCHAR(20) NOT NULL,
    artifact_uri        VARCHAR(500) NOT NULL,
    artifact_hash       CHAR(64) NOT NULL CHECK (length(artifact_hash) = 64),
    attributes          JSONB NOT NULL,
    masked_attributes   JSONB NOT NULL DEFAULT '[]',
    status              VARCHAR(20) NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active','revoked','expired')),
    signed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ,
    fee_assertion       JSONB NOT NULL DEFAULT '{"farmer_fees_total": 0}',
    CONSTRAINT uq_active_consent UNIQUE (farmer_id, counterparty_type, counterparty_id)
        WHERE status = 'active'
);
CREATE INDEX IF NOT EXISTS ix_consents_counterparty ON data_consents(counterparty_type, counterparty_id, status);

-- ================= fpo_attestations + vouches =================
CREATE TABLE IF NOT EXISTS fpo_attestations (
    id               BIGSERIAL PRIMARY KEY,
    membership_id    BIGINT NOT NULL REFERENCES fpo_memberships(id) ON DELETE CASCADE,
    attestation_type VARCHAR(30) NOT NULL CHECK (attestation_type IN ('staff','member')),
    attestor_user_id BIGINT NOT NULL REFERENCES users(id),
    score            SMALLINT CHECK (score BETWEEN 1 AND 5),
    statement        TEXT,
    status           VARCHAR(20) NOT NULL DEFAULT 'active'
                     CHECK (status IN ('active','suspect','frozen','rejected','contested')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_attest UNIQUE (membership_id, attestor_user_id, attestation_type)
);

-- ================= settlements + risk events =================
CREATE TABLE IF NOT EXISTS settlements (
    id                      BIGSERIAL PRIMARY KEY,
    loan_application_id     BIGINT NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    sale_value              NUMERIC(14,2) NOT NULL,
    fpo_facilitation_amt    NUMERIC(12,2) NOT NULL DEFAULT 0,
    platform_settlement_fee NUMERIC(12,2) NOT NULL DEFAULT 0,
    emi_paid                NUMERIC(12,2) NOT NULL DEFAULT 0,
    residual_to_farmer      NUMERIC(12,2) NOT NULL DEFAULT 0,
    receipt_json            JSONB NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk_events (
    id                   BIGSERIAL PRIMARY KEY,
    crop_cycle_id        BIGINT NOT NULL REFERENCES crop_cycles(id) ON DELETE CASCADE,
    event_type           VARCHAR(20) NOT NULL CHECK (event_type IN ('drought','flood','pest','hail','disease')),
    declared_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    severity             VARCHAR(10) NOT NULL CHECK (severity IN ('mild','moderate','severe')),
    loss_ratio           NUMERIC(4,3) CHECK (loss_ratio BETWEEN 0 AND 1),
    pmfby_claim_ref      VARCHAR(100),
    action               VARCHAR(20) NOT NULL DEFAULT 'recalibrate'
                         CHECK (action IN ('recalibrate','block_tranches','moratorium','pause'))
);