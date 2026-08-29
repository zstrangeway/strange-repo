"""The master resume scout writes for somebody who has not got one yet.

It exists because the grounding check needs the master's structure to know
what an employer is, and a format documented only in a README is one nobody
follows. Copying a file that already works is faster than reading about it.
"""

MASTER = """# Ada Lovelace

ada@example.com · London · github.com/example

## Skills

Python, Postgres, Terraform, Docker, SQL

## Experience

### Wilding Labs — Senior Platform Engineer

2021–2025

- Cut deploy time from 40 minutes to 4 by rebuilding the release pipeline
- Led a team of 3 through the billing migration, with no downtime
- Ran the Postgres upgrade across 40 services

### Thornfield Systems — Platform Engineer

2018–2021

- Built the Python services behind billing and invoicing
- Wrote the Terraform that describes every environment

## Education

### Imperial College London — BSc Computer Science

2014–2017
"""

# The two rules the format has, said where somebody editing the file will see
# them rather than only in the README.
GUIDANCE = """<!--
scout reads this file's structure, so two things matter:

  * every employer is an `### Employer — Job title` heading
  * every skill you claim is under `## Skills`

That is how tailoring knows what is yours. A draft naming an employer or a
skill that is not in here is refused before anything is written.
-->

"""
