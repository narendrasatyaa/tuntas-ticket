import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from tickets.models import Category, Ticket, TicketComment, UserProfile

def seed():
    print("Seeding roles & initial data for Tuntas...")

    # 1. Create Initial Categories
    categories_data = [
        {"name": "Hardware", "description": "Masalah perangkat keras seperti Laptop, Monitor, Keyboard, Printer, dll."},
        {"name": "Software", "description": "Masalah aplikasi kantor, OS, MS Office, Email Client, atau Lisensi."},
        {"name": "Network & Wi-Fi", "description": "Masalah koneksi Wi-Fi kantor, kabel LAN, VPN, atau Internet lemot."},
        {"name": "Account & Access", "description": "Permintaan reset password, pembuatan email baru, atau hak akses drive."},
        {"name": "Facility & Utility", "description": "Perangkat ruang rapat, proyektor, kabel extension, atau AC."},
        {"name": "Lainnya", "description": "Lainnya."},
    ]

    categories = {}
    for cat in categories_data:
        obj, created = Category.objects.get_or_create(
            name=cat["name"],
            defaults={"description": cat["description"]}
        )
        categories[cat["name"]] = obj

    # 2. Create Users with Explicit Roles

    # A. ADMIN (Superuser - Kelola Semua System)
    admin_user, _ = User.objects.get_or_create(username="admin", defaults={
        "email": "admin@tuntas.com",
        "first_name": "System",
        "last_name": "Administrator",
        "is_staff": True,
        "is_superuser": True
    })
    admin_user.set_password("password123")
    admin_user.is_superuser = True
    admin_user.is_staff = True
    admin_user.save()
    UserProfile.objects.update_or_create(user=admin_user, defaults={"role": UserProfile.Role.ADMIN, "department": "IT Management"})

    # B. IT LEAD / SUPERVISOR (Supervisor Support - Monitor SLA & Assign Team)
    lead_user, _ = User.objects.get_or_create(username="lead", defaults={
        "email": "lead@tuntas.com",
        "first_name": "Hendky",
        "last_name": "IT Supervisor",
        "is_staff": True,
        "is_superuser": False
    })
    lead_user.set_password("password123")
    lead_user.is_staff = True
    lead_user.is_superuser = False
    lead_user.save()
    UserProfile.objects.update_or_create(user=lead_user, defaults={"role": UserProfile.Role.IT_LEAD, "department": "IT Support Desk"})

    # C. TECHNICIAN (Teknisi Support - Fokus Fiksasi Kendala)
    tech_user, _ = User.objects.get_or_create(username="teknisi", defaults={
        "email": "teknisi@tuntas.com",
        "first_name": "Rizky",
        "last_name": "Support Fiksasi",
        "is_staff": True,
        "is_superuser": False
    })
    tech_user.set_password("password123")
    tech_user.is_staff = True
    tech_user.is_superuser = False
    tech_user.save()
    UserProfile.objects.update_or_create(user=tech_user, defaults={"role": UserProfile.Role.TECHNICIAN, "department": "Hardware & Network"})

    # D. REQUESTER (Karyawan - Fokus Aduan)
    budi_user, _ = User.objects.get_or_create(username="budi", defaults={
        "email": "budi@tuntas.com",
        "first_name": "Budi",
        "last_name": "Santoso",
        "is_staff": False,
        "is_superuser": False
    })
    budi_user.set_password("password123")
    budi_user.is_staff = False
    budi_user.is_superuser = False
    budi_user.save()
    UserProfile.objects.update_or_create(user=budi_user, defaults={"role": UserProfile.Role.REQUESTER, "department": "Keuangan"})

    print("Created 4 accounts with distinct roles:")
    print("1. admin (ADMIN / Superuser)")
    print("2. lead (IT_LEAD / Supervisor)")
    print("3. teknisi (TECHNICIAN / Fiksasi Kendala)")
    print("4. budi (REQUESTER / Fokus Aduan)")

    # 3. Create Sample Tickets
    t1, created1 = Ticket.objects.get_or_create(
        title="Laptop mati mendadak dan tidak mau charging",
        defaults={
            "description": "Laptop kerja ThinkPad saya mati tiba-tiba saat menyusun laporan bulanan. Lampu indikator charger tidak menyala.",
            "category": categories["Hardware"],
            "priority": Ticket.Priority.HIGH,
            "status": Ticket.Status.IN_PROGRESS,
            "created_by": budi_user,
            "assigned_to": tech_user
        }
    )

    if created1:
        TicketComment.objects.create(
            ticket=t1,
            author=tech_user,
            comment="Pemeriksaan awal fiksasi: Charger utama rusak, sedang disiapkan charger pengganti.",
            is_internal_note=False
        )
        TicketComment.objects.create(
            ticket=t1,
            author=lead_user,
            comment="Catatan Lead: Tolong segera proses penggantian unit jika IC power bermasalah.",
            is_internal_note=True
        )

    t2, created2 = Ticket.objects.get_or_create(
        title="Wi-Fi Lantai 2 sering terputus-putus",
        defaults={
            "description": "Koneksi Wi-Fi 'Kantor_Lantai2_5G' sering disconnect tiap 10 menit sekali sejak pagi ini.",
            "category": categories["Network & Wi-Fi"],
            "priority": Ticket.Priority.MEDIUM,
            "status": Ticket.Status.OPEN,
            "created_by": budi_user
        }
    )

    # 3. Tiket Sample 3: Status RESOLVED (Siap diberi penilaian atau re-open oleh Karyawan)
    t3, created3 = Ticket.objects.get_or_create(
        title="Permintaan Akun Email Baru untuk Staff Magang HR",
        defaults={
            "description": "Mohon dibuatkan akun Google Workspace baru untuk anak magang divisi HR: magang.hr@tuntas.com.",
            "category": categories["Account & Access"],
            "priority": Ticket.Priority.MEDIUM,
            "status": Ticket.Status.RESOLVED,
            "created_by": budi_user,
            "assigned_to": tech_user,
            "resolved_at": timezone.now(),
            "resolution_note": "Akun email magang.hr@tuntas.com telah dibuat dan kredensial sementara telah dikirimkan ke email PIC HR."
        }
    )

    print("Database seeding completed.")

if __name__ == '__main__':
    seed()
