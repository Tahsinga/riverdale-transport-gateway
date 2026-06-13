import os
import sys
import django
import re
from decimal import Decimal
import openpyxl

# ensure project root is on sys.path so Django settings package is importable
proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from config.models import RFIDTag, Student, Account
from django.contrib.auth.models import User


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s).strip().lower()) if s is not None else ''


def cell_for_row(col_index, row, key):
    k = _norm(key)
    idx = col_index.get(k)
    if idx is None:
        for hname, hidx in col_index.items():
            if not hname:
                continue
            if k == hname or k in hname or hname in k:
                idx = hidx
                break
    return row[idx] if idx is not None and idx < len(row) else None


def run(path):
    wb = openpyxl.load_workbook(filename=path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        print('No rows found')
        return

    # detect header row
    header_row_index = 0
    possible_markers = ('name', 'fullname', 'rfid', 'uid')
    for idx, r in enumerate(rows[:5]):
        normalized_cells = [_norm(c) for c in r]
        if any(any(marker in (cell or '') for cell in normalized_cells) for marker in possible_markers):
            header_row_index = idx
            break

    header = [_norm(c) for c in rows[header_row_index]]
    col_index = {name: idx for idx, name in enumerate(header)}

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(rows[header_row_index+1:], start=header_row_index+2):
        try:
            name = cell_for_row(col_index, row, 'name') or cell_for_row(col_index, row, 'fullname') or cell_for_row(col_index, row, 'full name')
            uid = cell_for_row(col_index, row, 'uid') or cell_for_row(col_index, row, 'rfid') or cell_for_row(col_index, row, 'rfid uid')
            username = cell_for_row(col_index, row, 'username')
            email = cell_for_row(col_index, row, 'email')
            balance = cell_for_row(col_index, row, 'balance') or cell_for_row(col_index, row, 'initialbalance') or cell_for_row(col_index, row, 'initial balance')
            grade = cell_for_row(col_index, row, 'class') or cell_for_row(col_index, row, 'grade')
            gender = cell_for_row(col_index, row, 'gender')
            register_no = cell_for_row(col_index, row, 'registerno') or cell_for_row(col_index, row, 'register_no') or cell_for_row(col_index, row, 'register no')
            section = cell_for_row(col_index, row, 'section')

            if not name:
                errors.append({'row': i, 'message': 'Missing name'})
                continue

            name = str(name).strip()
            tag = None
            if uid is not None and str(uid).strip() != '':
                uid = str(uid).strip()
                tag, _ = RFIDTag.objects.get_or_create(uid=uid)
                tag.assigned = True
                tag.save()
                student = Student.objects.filter(rfid_tag=tag).first()
            else:
                student = Student.objects.filter(name__iexact=name).first()

            user_obj = None
            if student:
                student.name = name
                if grade is not None:
                    student.grade = str(grade)
                if register_no is not None:
                    student.roll = str(register_no)
                if section is not None:
                    student.parent_contact = str(section)
                student.save()
                updated += 1
            else:
                if username or email:
                    uname = username or (str(email).split('@')[0] if email and '@' in str(email) else None)
                    if uname:
                        base = uname
                        suffix = 0
                        while User.objects.filter(username=uname).exists():
                            suffix += 1
                            uname = f"{base}{suffix}"
                        user_obj = User.objects.create(username=uname, email=email or '')
                        user_obj.set_unusable_password()
                        user_obj.save()
                student = Student.objects.create(
                    name=name,
                    rfid_tag=tag if tag is not None else None,
                    user=user_obj,
                    grade=grade or None,
                    roll=(str(register_no) if register_no is not None else (str(register_no) if register_no is not None else None)),
                    parent_contact=(str(section) if section is not None else None),
                )
                created += 1

            try:
                acct = Account.objects.get(student=student)
            except Account.DoesNotExist:
                acct = Account.objects.create(student=student, balance=0)

            if balance not in (None, ''):
                try:
                    acct.balance = Decimal(str(balance))
                    acct.save()
                except Exception:
                    errors.append({'row': i, 'message': 'Invalid balance value'})

        except Exception as e:
            errors.append({'row': i, 'message': str(e)})

    print({'created': created, 'updated': updated, 'errors': errors})


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python import_run.py <path_to_xlsx>')
        sys.exit(1)
    path = sys.argv[1]
    run(path)
