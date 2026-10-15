"""Crash-protection backups: pruning old rows and restoring a lost session."""

import csv
import datetime
import os
import time

from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class RecoveryMixin:
    """Part of BalanceTab: crash-protection backups: pruning old rows and restoring a lost session."""

    def prune_backup_file(self):
        if not os.path.exists(self.backup_path):
            return
        try:
            with open(self.backup_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                rows = list(reader)

            if not header:
                return
            valid_rows = []
            thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)

            for row in rows:
                if len(row) > 0:
                    try:
                        ts_str = row[0]
                        if len(ts_str) <= 19:
                            ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                        else:
                            ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
                        if ts >= thirty_days_ago:
                            valid_rows.append(row)
                    except:
                        valid_rows.append(row)

            with open(self.backup_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(valid_rows)
        except:
            pass

    def scan_backup_sessions(self):
        import re

        target_path = self.backup_path
        if not os.path.exists(target_path):
            alt_name = re.sub(r"_\(\d+\)_Backup\.csv$", "_Backup.csv", target_path)
            if os.path.exists(alt_name):
                target_path = alt_name
            else:
                backup_dir = os.path.dirname(target_path)
                base_clean = re.sub(r"\s*\(\d+\)$", "", self.tab_name).replace(" ", "_")
                possible = os.path.join(backup_dir, f"{base_clean}_Backup.csv")
                if os.path.exists(possible):
                    target_path = possible
                else:
                    return []
        self._target_recovery_file = target_path
        sessions = []
        try:
            with open(target_path, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                rows = list(reader)
            current_session = None
            last_dur = -1.0
            for idx, row in enumerate(rows):
                if len(row) >= 4:
                    try:
                        ts, dur = row[0], float(row[1])
                        if current_session is None or dur < last_dur:
                            if current_session:
                                current_session["end_idx"] = idx - 1
                                sessions.append(current_session)
                            current_session = {"start_idx": idx, "start_ts": ts, "end_ts": ts, "points": 0}
                        current_session["end_ts"] = ts
                        current_session["points"] += 1
                        last_dur = dur
                    except:
                        pass
            if current_session:
                current_session["end_idx"] = len(rows) - 1
                sessions.append(current_session)
        except:
            pass
        return sessions

    def prompt_session_recovery(self):
        sessions = self.scan_backup_sessions()
        if not sessions:
            return QMessageBox.information(self, "Recovery", "No recovery sessions found.")

        display_sessions = list(reversed(sessions))

        dialog = QDialog(self)
        dialog.setWindowTitle("Restore Session")
        dialog.setMinimumSize(450, 320)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            QLabel("Multiple recording sessions were found. Please select which one to restore:")
        )

        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        bg = QButtonGroup(dialog)
        total_sessions = len(sessions)
        for i, s in enumerate(display_sessions):
            orig_num = total_sessions - i
            tag = " (Newest)" if i == 0 else (" (Oldest)" if i == total_sessions - 1 else "")
            rb = QRadioButton(
                f"Session {orig_num}{tag} | {s['start_ts']} -> {s['end_ts']} | {s['points']} pts"
            )
            if i == 0:
                rb.setChecked(True)
            bg.addButton(rb, i)
            scroll_layout.addWidget(rb)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_restore = QPushButton("Restore Selected")
        btn_ignore = QPushButton("Ignore")
        btn_layout.addWidget(btn_restore)
        btn_layout.addWidget(btn_ignore)
        layout.addLayout(btn_layout)

        recovery_file = getattr(self, "_target_recovery_file", self.backup_path)

        def do_restore():
            idx = bg.checkedId()
            if idx >= 0:
                s = display_sessions[idx]
                try:
                    with open(recovery_file, newline="", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        next(reader, None)
                        rows = list(reader)
                    for r_idx in range(s["start_idx"], s["end_idx"] + 1):
                        row = rows[r_idx]
                        if len(row) >= 4:
                            try:
                                self.timestamps.append(row[0])
                                dur = float(row[1])
                                self.times_min.append(dur)
                                self.times_sec.append(dur * 60.0)
                                self.weights.append(float(row[2]))
                                flw = row[3]
                                if flw:
                                    self.flow_rates.append(float(flw))
                            except:
                                pass
                    if self.times_sec:
                        self.start_time = time.time() - self.times_sec[-1]
                        self.last_recorded_time = self.times_sec[-1]
                        self.unsaved_changes = True
                except:
                    pass
            dialog.accept()

        btn_restore.clicked.connect(do_restore)
        btn_ignore.clicked.connect(dialog.reject)
        dialog.exec()
