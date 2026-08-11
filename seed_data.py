import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from tickets.models import Category, Ticket, TicketComment

def seed():
    print("Seeding initial data for Tuntas...")

    # 1. Create Initial Categories
    categories_data = [
        {"name": "Hardware", "description": "Masalah perangkat keras seperti Laptop, Monitor, Keyboard, Printer, dll."},
        {"name": "Software", "description": "Masalah aplikasi kantor, OS, MS Office, Email Client, atau Lisensi."},
        {"name": "Network & Wi-Fi", "description": "Masalah koneksi Wi-Fi kantor, kabel LAN, VPN, atau Internet lemot."},
        {"name": "Account & Access", "description": "Permintaan reset password, pembuatan email baru, atau hak akses drive."},
        {"name": "Facility & Utility", "description": "Perangkat ruang rapat, proyektor, kabel extension, atau AC."},
    ]

    categories = {}
    for cat in categories_data:
        obj, created = Category.objects.get_or_create(
            name=cat["name"],
            defaults={"description": cat["description"]}
        )
        categories[cat["name"]] = obj
        print(f"Category '{cat['name']}' ready.")

    # 2. Create Sample Users
    # Admin / IT Manager
    admin_user, _ = User.objects.get_or_create(username="admin", defaults={
        "email": "admin@kantor.com",
        "first_name": "Admin",
        "last_name": "IT Lead",
        "is_staff": True,
        "is_superuser": True
    })
    admin_user.set_password("password123")
    admin_user.save()

    # IT Technician
    tech_user, _ = User.objects.get_or_create(username="teknisi_it", defaults={
        "email": "teknisi@kantor.com",
        "first_name": "Rizky",
        "last_name": "Support",
        "is_staff": True
    })
    tech_user.set_password("password123")
    tech_user.save()

    # Requester / Employee
    user_budi, _ = User.objects.get_or_create(username="budi_requester", defaults={
        "email": "budi@kantor.com",
        "first_name": "Budi",
        "last_name": "Santoso",
        "is_staff": False
    })
    user_budi.set_password("password123")
    user_budi.save()

    print("Users created: admin, teknisi_it, budi_requester (password: password123)")

    # 3. Create Sample Tickets
    t1, created1 = Ticket.objects.get_or_create(
        title="Laptop mati mendadak dan tidak mau charging",
        defaults={
            "description": "Laptop kerja ThinkPad saya mati tiba-tiba saat menyusun laporan bulanan. Lampu indikator charger tidak menyala.",
            "category": categories["Hardware"],
            "priority": Ticket.Priority.HIGH,
            "status": Ticket.Status.IN_PROGRESS,
            "created_by": user_budi,
            "assigned_to": tech_user
        }
    )

    if created1:
        TicketComment.objects.create(
            ticket=t1,
            author=tech_user,
            comment="Sedang saya cek dengan adaptor cadangan di meja IT.",
            is_internal_note=False
        )
        TicketComment.objects.create(
            ticket=t1,
            author=tech_user,
            comment="Kemungkinan ic power rusak, perlu klaim garansi vendor.",
            is_internal_note=True
        )

    t2, created2 = Ticket.objects.get_or_create(
        title="Wi-Fi Lantai 2 sering terputus-putus",
        defaults={
            "description": "Koneksi Wi-Fi 'Kantor_Lantai2_5G' sering disconnect tiap 10 menit sekali sejak pagi ini.",
            "category": categories["Network & Wi-Fi"],
            "priority": Ticket.Priority.MEDIUM,
            "status": Ticket.Status.OPEN,
            "created_by": user_budi
        }
    )

    t3, created3 = Ticket.objects.get_or_create(
        title="Lupa Password Email Kantor",
        defaults={
            "description": "Mohon bantuan reset password email budi@kantor.com karena terkunci setelah salah ketik 3 kali.",
            "category": categories["Account & Access"],
            "priority": Ticket.Priority.URGENT,
            "status": Ticket.Status.RESOLVED,
            "created_by": user_budi,
            "assigned_to": tech_user
        }
    )

    if created3:
        TicketComment.objects.create(
            ticket=t3,
            author=tech_user,
            comment="Password sementara telah dikirimkan via WhatsApp terverifikasi. Silakan ganti password saat login pertama.",
            is_internal_note=False
        )

    print("Sample tickets created successfully.")

if __name__ == '__main__':
    seed()
