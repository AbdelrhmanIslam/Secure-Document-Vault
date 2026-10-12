from extensions import db
from datetime import datetime

class User(db.Model):
    ROLE_ADMIN = 'Admin'
    ROLE_MANAGER = 'Manager'
    ROLE_USER = 'User'
    ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_USER)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_USER)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    twofa_secret = db.Column(db.String(32), nullable=False, default='')
    twofa_enabled = db.Column(db.Boolean, default=False)
    oauth_provider = db.Column(db.String(20), nullable=True)
    oauth_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    documents = db.relationship(
        'Document',
        back_populates='uploader',
        cascade='all, delete-orphan',
        passive_deletes=True,
        foreign_keys='Document.uploader_id'
    )

    def can_manage_users(self):
        return self.role == self.ROLE_ADMIN

    def can_review_documents(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_MANAGER)

    @property
    def is_oauth_only(self):
        return self.password_hash == 'OAUTH_ONLY'

class Document(db.Model):
    STATUS_PENDING = 'Pending'
    STATUS_APPROVED = 'Approved'
    STATUS_REJECTED = 'Rejected'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    encrypted_path = db.Column(db.String(300), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    signature = db.Column(db.Text, nullable=False)
    
    uploader = db.relationship('User', back_populates='documents', foreign_keys=[uploader_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])