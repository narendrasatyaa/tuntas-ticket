import os
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nama Kategori")
    description = models.TextField(blank=True, null=True, verbose_name="Deskripsi")
    is_active = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategori Tiket"
        ordering = ['name']

    def __str__(self):
        return self.name


class Ticket(models.Model):
    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    ticket_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False, 
        verbose_name="ID Tiket"
    )
    title = models.CharField(max_length=200, verbose_name="Judul Aduan")
    description = models.TextField(verbose_name="Deskripsi Masalah")
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT, 
        related_name='tickets',
        verbose_name="Kategori"
    )
    priority = models.CharField(
        max_length=10, 
        choices=Priority.choices, 
        default=Priority.MEDIUM,
        verbose_name="Prioritas"
    )
    status = models.CharField(
        max_length=15, 
        choices=Status.choices, 
        default=Status.OPEN,
        verbose_name="Status"
    )

    # Relasi User
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='submitted_tickets',
        verbose_name="Pelapor"
    )
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tickets',
        verbose_name="Teknisi IT"
    )

    # Lampiran file (Gambar & Dokumen pendukung)
    attachment = models.FileField(
        upload_to='ticket_attachments/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx', 'zip']
            )
        ],
        verbose_name="Lampiran"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Diperbarui Pada")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Diselesaikan Pada")

    class Meta:
        verbose_name = "Tiket"
        verbose_name_plural = "Daftar Tiket"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.ticket_id}] {self.title}"

    def save(self, *args, **kwargs):
        # Auto-generate Ticket ID unik jika belum ada (Contoh: TIX-20260811-XXXX)
        if not self.ticket_id:
            import uuid
            from django.utils import timezone
            today_str = timezone.now().strftime('%Y%m%d')
            unique_hash = uuid.uuid4().hex[:4].upper()
            self.ticket_id = f"TIX-{today_str}-{unique_hash}"
            
        super().save(*args, **kwargs)

    @property
    def filename(self):
        if self.attachment:
            return os.path.basename(self.attachment.name)
        return None


class TicketComment(models.Model):
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='comments',
        verbose_name="Tiket"
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name="Penulis Catatan"
    )
    comment = models.TextField(verbose_name="Komentar / Catatan Penanganan")
    is_internal_note = models.BooleanField(
        default=False, 
        verbose_name="Catatan Internal IT",
        help_text="Jika dicentang, hanya tim IT yang bisa melihat catatan ini."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dibuat Pada")

    class Meta:
        verbose_name = "Komentar Tiket"
        verbose_name_plural = "Komentar Tiket"
        ordering = ['created_at']

    def __str__(self):
        return f"Komentar oleh {self.author.username} pada {self.ticket.ticket_id}"