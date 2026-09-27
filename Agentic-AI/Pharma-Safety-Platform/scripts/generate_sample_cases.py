"""
Generates real PDFs, shaped like MedWatch 3500A adverse-event reports,
filled with realistic-but-entirely-fictional patient data. Deliberately
includes repeated drug-event pairs (DrugX + cardiac arrest, 3 times) so
signal detection has real accumulated data to compute against, not just
a single case that can never produce a meaningful 2x2 table.
"""

from pathlib import Path

from fpdf import FPDF

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "sample_cases"


def build_case_pdf(path: Path, fields: dict) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "MEDWATCH-STYLE ADVERSE EVENT REPORT (FICTIONAL DEMO DATA)")
    pdf.ln(12)
    pdf.set_font("Helvetica", "", 11)

    for label, value in fields.items():
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"{label}:")
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, str(value))
        pdf.ln(1)

    pdf.output(str(path))


CASES = {
    # -- DrugX + cardiac arrest, three real cases: this is the pair signal
    # detection should actually flag once run against the accumulated data --
    "case_001_drugx_cardiac_arrest_a.pdf": {
        "Report ID": "DEMO-CASE-001", "Patient Initials": "J.D.", "Patient Sex": "Male", "Patient Age": "54",
        "Suspect Product": "ExampleDrugX 10mg tablets", "Concomitant Medications": "ExampleDrugY 5mg",
        "Event Description": "Patient collapsed at home roughly 45 minutes after the second dose. "
                              "Found in cardiac arrest by paramedics, resuscitated, admitted to ICU for four days.",
        "Outcome": "Hospitalized. Event resolved with sequelae.",
        "Reporter": "Treating physician",
    },
    "case_002_drugx_cardiac_arrest_b.pdf": {
        "Report ID": "DEMO-CASE-002", "Patient Initials": "M.S.", "Patient Sex": "Female", "Patient Age": "61",
        "Suspect Product": "ExampleDrugX 10mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Sudden cardiac arrest approximately one hour after taking ExampleDrugX. "
                              "Emergency resuscitation successful, admitted to cardiac ICU for six days.",
        "Outcome": "Hospitalized, life-threatening. Event resolved.",
        "Reporter": "Hospital pharmacovigilance office",
    },
    "case_003_drugx_cardiac_arrest_c.pdf": {
        "Report ID": "DEMO-CASE-003", "Patient Initials": "T.K.", "Patient Sex": "Male", "Patient Age": "48",
        "Suspect Product": "ExampleDrugX 10mg tablets", "Concomitant Medications": "ExampleDrugY 5mg",
        "Event Description": "Went into cardiac arrest within two hours of the third dose of ExampleDrugX. "
                              "Bystander CPR started immediately, patient survived, admitted to ICU.",
        "Outcome": "Hospitalized. Event resolved with sequelae.",
        "Reporter": "Patient's spouse, via consumer hotline",
    },

    "case_009_drugx_cardiac_arrest_d.pdf": {
        "Report ID": "DEMO-CASE-009", "Patient Initials": "F.W.", "Patient Sex": "Male", "Patient Age": "59",
        "Suspect Product": "ExampleDrugX 10mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Collapsed in cardiac arrest roughly 90 minutes after taking ExampleDrugX. "
                              "Paramedics resuscitated on scene, admitted to ICU for five days.",
        "Outcome": "Hospitalized. Event resolved with sequelae.",
        "Reporter": "Emergency department physician",
    },
    "case_010_drugx_cardiac_arrest_e.pdf": {
        "Report ID": "DEMO-CASE-010", "Patient Initials": "S.O.", "Patient Sex": "Female", "Patient Age": "52",
        "Suspect Product": "ExampleDrugX 10mg tablets", "Concomitant Medications": "ExampleDrugY 5mg",
        "Event Description": "Sudden cardiac arrest at home, roughly one hour after the fourth dose of "
                              "ExampleDrugX. Family performed CPR until paramedics arrived, resuscitated, "
                              "admitted to cardiac ICU.",
        "Outcome": "Hospitalized, life-threatening. Event resolved with sequelae.",
        "Reporter": "Treating physician",
    },

    # -- DrugX, mild/non-serious event, for contrast --
    "case_004_drugx_mild_nausea.pdf": {
        "Report ID": "DEMO-CASE-004", "Patient Initials": "A.K.", "Patient Sex": "Female", "Patient Age": "31",
        "Suspect Product": "ExampleDrugX 10mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Mild nausea starting within an hour of the first dose. No vomiting. "
                              "Resolved without treatment the same day.",
        "Outcome": "Not hospitalized. Event resolved without treatment.",
        "Reporter": "Patient, via manufacturer consumer hotline",
    },

    # -- DrugZ, a different serious event, unrelated to the DrugX signal --
    "case_005_drugz_severe_skin_reaction.pdf": {
        "Report ID": "DEMO-CASE-005", "Patient Initials": "R.M.", "Patient Sex": "Male", "Patient Age": "67",
        "Suspect Product": "ExampleDrugZ 25mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Approximately ten days after starting ExampleDrugZ, widespread skin blistering "
                              "and peeling affecting roughly 15 percent of body surface area, with mucosal "
                              "involvement. Admitted to the burn unit for wound care.",
        "Outcome": "Hospitalized, life-threatening. Event ongoing.",
        "Reporter": "Treating dermatologist",
    },

    # -- background noise: different drugs, non-serious, mild events --
    "case_006_drugy_headache.pdf": {
        "Report ID": "DEMO-CASE-006", "Patient Initials": "L.P.", "Patient Sex": "Female", "Patient Age": "42",
        "Suspect Product": "ExampleDrugY 5mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Mild headache for two days after starting ExampleDrugY. No other symptoms.",
        "Outcome": "Not hospitalized. Event resolved without treatment.",
        "Reporter": "Patient",
    },
    "case_007_drugy_nausea.pdf": {
        "Report ID": "DEMO-CASE-007", "Patient Initials": "G.H.", "Patient Sex": "Male", "Patient Age": "55",
        "Suspect Product": "ExampleDrugY 5mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Mild nausea after the first two doses of ExampleDrugY. Resolved on its own.",
        "Outcome": "Not hospitalized. Event resolved without treatment.",
        "Reporter": "Patient",
    },
    "case_008_drugz_nausea.pdf": {
        "Report ID": "DEMO-CASE-008", "Patient Initials": "N.B.", "Patient Sex": "Female", "Patient Age": "38",
        "Suspect Product": "ExampleDrugZ 25mg tablets", "Concomitant Medications": "None reported",
        "Event Description": "Mild nausea reported after starting ExampleDrugZ, resolved within a day.",
        "Outcome": "Not hospitalized. Event resolved without treatment.",
        "Reporter": "Patient",
    },
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, fields in CASES.items():
        path = OUTPUT_DIR / filename
        build_case_pdf(path, fields)
        print(f"Wrote {path.name} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
