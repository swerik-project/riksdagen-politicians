"""
throw ERROR on inconsistencies on our side

WARN on upstream errors
"""
from datetime import datetime
from lxml import etree
from pathlib import Path
from pyriksdagen.db import load_metadata
from pyriksdagen.utils import (
    get_doc_dates,
    parse_protocol,
    protocol_iterators,
)
from pytest_cfg_fetcher.fetch import fetch_config
import pandas as pd
import unittest
import warnings
import yaml




class DuplicateWarning(Warning):
    def __init__(self, duplicate_df):
        self.message = f"Following duplicates found\n{duplicate_df}"

    def __str__(self):
        return self.message


class MissingPersonWarning(Warning):
    def __init__(self, missing_persons):
        self.message = f"The following people are missing from the corpus metadata (person.csv)\n{missing_persons}"

    def __str__(self):
        return self.message


class MissingNameWarning(Warning):
    def __init__(self, missing_names):
        self.message = f"The following people are missing from the corpus metadata (name.csv)\n{missing_names}"

    def __str__(self):
        return self.message


class MissingLocationWarning(Warning):
    def __init__(self, missing_location):
        self.message = f"The following people are missing from the corpus metadata (location_specifier.csv)\n{missing_location}"

    def __str__(self):
        return self.message


class MissingMemberWarning(Warning):
    def __init__(self, missing_member):
        self.message = f"The following people are missing members (member_of_parliament.csv)\n{missing_member}"

    def __str__(self):
        return self.message


class MissingPartyWarning(Warning):
    def __init__(self, missing_location):
        self.message = f"The following people are missing from the corpus metadata (party_affiliation.csv)\n{missing_location}"

    def __str__(self):
        return self.message


class CatalogIntegrityWarning(Warning):
    def __init__(self, issue):
        self.message = f"There's an integrity issue --| {issue} |-- maybe fix that."

    def __str__(self):
        return self.message




class Test(unittest.TestCase):
    #
    # ---> Helper functions
    #
    def get_duplicates(self, df_name, columns):
        """
        Return a the df of a csv,  a df of unique rows, and a df of duplicates.
        """
        p = Path(".") / "data"
        path = p / f"{df_name}.csv"
        df = pd.read_csv(path)

        df_duplicate = df[df.duplicated(columns, keep=False)]
        df_unique = df.drop_duplicates(columns)
        return df, df_unique, df_duplicate


    def get_emil(self):
        """
        Return a df of hand-checked (by Emil) "members of parliament" metadata.
        """
        emil_df = pd.read_csv('test/data/known-mps-catalog.csv', sep=';')
        return emil_df


    def get_meta_df(self, df_name):
        """
        Return csv as a df by name.
        """
        p = Path(".") / "data"
        path = p / f"{df_name}.csv"
        df = pd.read_csv(path)
        return df


    def write_error_df(self, df_name, errs, outpath):
        """
        Take a list of errors and write the output as a dataframe
        """
        now = datetime.now().strftime('%Y%m%d-%H%M%S')
        errs.to_csv(f"{outpath}/{now}_db_{df_name}.csv", sep=';', index=False)

    #
    # ---> Tests
    #
    def test_government(self):
        """
        test no duplicate rows in government data
        """
        columns = ["start", "end"]
        df_name = "government"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, columns)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_member_of_parliament(self):
        """
        Test no duplicates in MP data
        """
        columns = ["person_id", "start", "end"]
        df_name = "member_of_parliament"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, columns)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_minister(self):
        """
        test no duplicates in Minister data
        """
        df_name = "minister"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, None)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_party_affiliation(self):
        """
        test no duplicates in party data
        """
        columns = ["person_id", "start", "end"]
        df_name = "party_affiliation"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, columns)

        if len(df) != len(df_unique):
            warnings.warn(str(df_duplicate), DuplicateWarning)

        df, df_unique, df_duplicate = self.get_duplicates(df_name, None)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_person(self):
        """
        test no duplicates in person
        """
        columns = ["person_id"]
        df_name = "person"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, columns)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_speaker(self):
        """
        test no duplicates in speaker data
        """
        columns = ["start", "end", "role"]
        df_name = "speaker"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, columns)

        if len(df) != len(df_unique):
            warnings.warn(str(df_duplicate), DuplicateWarning)

        df, df_unique, df_duplicate = self.get_duplicates(df_name, None)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_twitter(self):
        """
        test no duplicates in twitter data
        """
        df_name = "twitter"
        df, df_unique, df_duplicate = self.get_duplicates(df_name, None)

        if len(df) != len(df_unique):
            warnings.warn(str(df_duplicate), DuplicateWarning)

        df, df_unique, df_duplicate = self.get_duplicates(df_name, None)
        self.assertEqual(len(df), len(df_unique), df_duplicate)


    def test_emil_integrity(self):
        """
        test integrity of the known-mp-catalog
        """
        emil = self.get_emil()
        config = fetch_config("db")

        person_id_issue = emil[(emil['person_id'].isna()) | (emil['person_id'] == "Q00FEL00")]
        if not person_id_issue.empty:
            warnings.warn(f'{len(person_id_issue)} person_id issues', CatalogIntegrityWarning)
            if config and congif["write_catalog_integrity"]:
                self.write_error_df("swerik-id-issue", person_id_issue, config["test_out_dir"])

        birthdate_NA = emil[(emil['born'].isna()) | (emil['born'] == "Multival")]
        if not birthdate_NA.empty:
            warnings.warn(f"{len(birthdate_NA)} birthdates missing", CatalogIntegrityWarning)
            if config and congif["write_catalog_integrity"]:
                self.write_error_df("missing-birthdate", birthdate_NA, config["test_out_dir"])

        self.assertEqual(len(person_id_issue), 0, person_id_issue)
        self.assertEqual(len(birthdate_NA), 0, birthdate_NA)


    def test_cf_emil_person(self):
        """
        test that every entry on the person catalog is in the person.csv file
        """
        df_name = "person"
        df = self.get_meta_df(df_name)
        emil = self.get_emil()
        config = fetch_config("db")

        missing_persons = pd.DataFrame(columns=list(emil.columns))
        for i, row in emil.iterrows():
            if row['person_id'] not in df['person_id'].unique():
                missing_persons.loc[len(missing_persons)] = row

        if not missing_persons.empty:
            warnings.warn(str(missing_persons), MissingPersonWarning)
            if config and config['write_missing_person']:
                self.write_error_df(df_name, missing_persons, config["test_out_dir"])

        self.assertTrue(missing_persons.empty, missing_persons)


    def test_cf_emil_name(self):
        """
        test that every entry on the person catalog is in the name.csv file
        """
        df_name = "name"
        df = self.get_meta_df(df_name)
        emil = self.get_emil()
        config = fetch_config("db")

        missing_names = pd.DataFrame(columns=list(emil.columns))
        for i, row in emil.iterrows():
            if row['person_id'] not in df['person_id'].unique():
                missing_names.loc[len(missing_names)] = row

        if not missing_names.empty:
            warnings.warn(str(missing_names), MissingNameWarning)
            if config and config['write_missing_name']:
                self.write_missing(df_name, missing_names, config["test_out_dir"])

        self.assertTrue(missing_names.empty, missing_names)


    def test_cf_known_iorter_metadata(self):
        """
        test that every entry on the person catalog is in the location_specifier.csv with the same location
        """
        df_name = "location_specifier"
        df = self.get_meta_df(df_name)
        iorter = pd.read_csv("test/data/known-iorter.csv", sep=";")
        config = fetch_config("db")

        missing_locations = pd.DataFrame(columns=list(iorter.columns))
        for i, row in iorter.iterrows():
            filtered = df.loc[(df["person_id"] == row["person_id"]) & (df["location"] == row["iort"])]
            if len(filtered) < 1:
                missing_locations.loc[len(missing_locations)] = row

        if not missing_locations.empty:
            warnings.warn(str(missing_locations), MissingLocationWarning)
            if config and config['write_missing_iorter']:
                self.write_error_df(df_name, missing_locations, config["test_out_dir"])

        self.assertTrue(missing_locations.empty, missing_locations)


    def test_cf_emil_member(self):
        """
        test that every entry on the person catalog is in the member_of_parliament.csv file
        """
        df_name = "member_of_parliament"
        df = self.get_meta_df(df_name)
        emil = self.get_emil()
        config = fetch_config("db")

        missing_members = pd.DataFrame(columns=list(emil.columns))
        for i, row in emil.iterrows():
            if row['person_id'] not in df['person_id'].unique():
                missing_members.loc[len(missing_members)] = row

        if not missing_members.empty:
            warnings.warn(str(missing_members), MissingMemberWarning)
            if config and congig['write_missing_mep']:
                self.write_error_df(df_name, missing_members, config["test_out_dir"])

        self.assertTrue(missing_members.empty, missing_members)


    @unittest.skip("Skipping party_affiliation test")
    def test_cf_emil_party(self):
        """
        test that every entry on the person catalog is in the party_affiliation.csv file
        """
        df_name = "party_affiliation"
        df = self.get_meta_df(df_name)
        emil = self.get_emil()
        config = fetch_config("db")

        missing_parties = pd.DataFrame(columns=list(emil.columns))
        for i, row in emil.iterrows():
            if row['person_id'] not in df['person_id'].unique():
                missing_parties.loc[len(missing_parties)] = row

        if not missing_parties.empty:
            warnings.warn(str(missing_parties), MissingPartyWarning)
            if config and config["write_missing_party"]:
                self.write_error_df(df_name, missing_parties, config["test_out_dir"])

        self.assertTrue(missing_parties.empty, missing_parties)


    @unittest.skip
    def test_session_dates(self):
        """
        test that all protocols are in the known session dates

        session dates scraped from protocols -- necessary? useful?
        """
        dates_df = pd.read_csv("test/data/session-dates.csv", sep=';')
        protocols = sorted(list(protocol_iterators("corpus/protocols/", start=1867, end=2022)))
        config = fetch_config("db")

        date_counter = 0
        err = False
        for protocol in protocols:
            E, dates = get_doc_dates(protocol)
            if E:
                err = True
        if err:
            rows = []
            cols = ["protocol", "date"]
            for i, r in dates_df.iterrows():
                root = parse_protocol(r['protocol'])
                d = r["date"]
                date_match = root.findall(f'{tei_ns}docDate[@when="{d}"]')
                if len(date_match) != 1:
                    rows.append([r['protocol']. r['date']])
            if len(rows) > 0:
                if config and config["write_unknown_dates"]:
                    df = pd.DataFrame(rows, columns=cols)
                    self.write_error_df("session-dates", df, config["test_out_dir"])

            self.assertEqual(
                len(rows), 0,
                f"{len(rows)} date issues // dates not in the known session dates csv")




if __name__ == '__main__':
    unittest.main()
