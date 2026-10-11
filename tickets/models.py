import os
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class UserProfile(models.Model):
    class Role(models.TextChoices):
        REQUESTER = 'REQUESTER', 'Karyawan (Pelapor Aduan)'
        TECHNICIAN = 'TECHNICIAN', 'Teknisi IT (Fiksasi Kendala)'
        IT_LEAD = 'IT_LEAD', 'IT Lead / Supervisor Support'
        ADMIN = 'ADMIN', 'Administrator (Kelola Semua System)'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REQUESTER)
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="Departemen / Divisi")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


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
    due_date = models.DateTimeField(null=True, blank=True, verbose_name="Batas Waktu SLA")

    # Solusi Resmi & Verifikasi (Diisi oleh Teknisi saat Resolve)
    resolution_note = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Catatan Solusi / Tindakan Perbaikan"
    )

    # Penilaian Kepuasan CSAT (Diisi oleh Karyawan/Pelapor saat tiket Resolved/Closed)
    rating = models.PositiveSmallIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Rating Kepuasan (1-5)"
    )
    rating_feedback = models.TextField(
        null=True, 
        blank=True, 
        verbose_name="Ulasan Penilaian"
    )
    rated_at = models.DateTimeField(null=True, blank=True, verbose_name="Waktu Penilaian")

    class Meta:
        verbose_name = "Tiket"
        verbose_name_plural = "Daftar Tiket"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.ticket_id}] {self.title}"

    def save(self, *args, **kwargs):
        import uuid
        from datetime import timedelta
        from django.utils import timezone

        is_new = self._state.adding or not self.pk

        # Auto-generate Ticket ID unik jika belum ada (Contoh: TIX-20260811-XXXX)
        if not self.ticket_id:
            today_str = timezone.now().strftime('%Y%m%d')
            unique_hash = uuid.uuid4().hex[:4].upper()
            self.ticket_id = f"TIX-{today_str}-{unique_hash}"

        # Hitung SLA Due Date otomatis saat tiket pertama kali dibuat
        if is_new and not self.due_date:
            now = timezone.now()
            sla_hours = {
                self.Priority.URGENT: 4,
                self.Priority.HIGH: 12,
                self.Priority.MEDIUM: 24,
                self.Priority.LOW: 48,
            }
            hours = sla_hours.get(self.priority, 24)
            self.due_date = now + timedelta(hours=hours)

        super().save(*args, **kwargs)

    @property
    def is_sla_breached(self):
        """Mengecek apakah tiket melewati target batas waktu SLA."""
        if not self.due_date:
            return False
        from django.utils import timezone
        if self.resolved_at:
            return self.resolved_at > self.due_date
        if self.status in [self.Status.RESOLVED, self.Status.CLOSED]:
            return False
        return timezone.now() > self.due_date

    @property
    def time_until_sla(self):
        """Sisa waktu atau waktu keterlambatan SLA dalam format yang mudah dipahami."""
        if not self.due_date:
            return None
        from django.utils import timezone
        now = timezone.now()
        target = self.resolved_at if (self.status in [self.Status.RESOLVED, self.Status.CLOSED] and self.resolved_at) else now
        
        diff = self.due_date - target
        total_seconds = int(diff.total_seconds())
        if total_seconds < 0:
            late_hours = abs(total_seconds) // 3600
            late_minutes = (abs(total_seconds) % 3600) // 60
            if late_hours > 0:
                return f"Lewat {late_hours}j {late_minutes}m"
            return f"Lewat {late_minutes}m"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if hours > 0:
                return f"Sisa {hours}j {minutes}m"
            return f"Sisa {minutes}m"

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