# SPDX-License-Identifier: MIT
"""Exact upstream method excerpts; compiled with dummy bases in offline tests.

DataCite: RDM d4a4ef21; draft files: invenio-drafts-resources11.0.3.
See contracts/schemas/zenodo-modern/README.md for provenance and limits.
"""

# Exact notices from the DataCite source excerpt:
# SPDX-FileCopyrightText: 2021-2024 CERN.
# SPDX-FileCopyrightText: 2023 Northwestern University.
# SPDX-FileCopyrightText: 2023-2024 Graz University of Technology.
class DataCitePIDProvider:
    def validate(self, record, identifier=None, provider=None, **kwargs):
        """Validate the attributes of the identifier.

        :returns: A tuple (success, errors). `success` is a bool that specifies
                  if the validation was successful. `errors` is a list of
                  error dicts of the form:
                  `{"field": <field>, "messages: ["<msgA1>", ...]}`.
        """
        # success is unused, but naming it _ would interfere with lazy_gettext as _
        success, errors = super().validate(record, identifier, provider, **kwargs)

        # Validate identifier
        # Checking if the identifier is not None is crucial because not all records at
        # this point will have a DOI identifier (and that is fine in the case of initial
        # creation)
        if identifier is not None:
            # Format check
            try:
                self.client.api.check_doi(identifier)
            except ValueError as e:
                # modifies the error in errors in-place
                self._insert_pid_type_error_msg(errors, str(e))

        # Validate record
        if not record.get("metadata", {}).get("publisher"):
            errors.append(
                {
                    "field": "metadata.publisher",
                    "messages": [
                        _("Missing publisher field required for DOI registration.")
                    ],
                }
            )

        return not bool(errors), errors

# Exact notice from the draft-files source excerpt:
# SPDX-FileCopyrightText: 2021-2025 CERN.
class BaseRecordFilesComponent:
    def update_draft(self, identity, data=None, record=None, errors=None):
        """Assigns files.enabled and warns if files are missing.

        NOTE: `record` actually refers to the draft
              (this interface is used in records-resources and rdm-records)
        """
        draft = record
        draft_files = self.get_record_files(draft)
        default_preview = data.get(self.files_data_key, {}).get("default_preview")
        can_toggle_files = self.service.check_permission(
            identity, "manage_files", record=draft
        )

        enabled = data.get(self.files_data_key, {}).get(
            "enabled", self.service.config.default_files_enabled
        )

        if draft_files.enabled != enabled:
            if not can_toggle_files:
                errors.append(
                    {
                        "field": f"{self.files_data_key}.enabled",
                        "messages": [
                            _("You don't have permissions to manage files options.")
                        ],
                    }
                )
                return  # exit early

        try:
            self.assign_files_enabled(draft, enabled)
        except ValidationError as e:
            errors.append(
                {"field": f"{self.files_data_key}.enabled", "messages": e.messages}
            )
            return  # exit early

        if draft_files.enabled and not draft_files.items():
            if can_toggle_files:
                my_message = _(
                    "Missing uploaded files. To disable files for this record please mark it as metadata-only."
                )
            else:
                my_message = _("Missing uploaded files.")
            errors.append(
                {
                    "field": f"{self.files_data_key}.enabled",
                    "messages": [my_message],
                }
            )

        try:
            self.assign_files_default_preview(
                draft,
                default_preview,
            )
        except ValidationError as e:
            errors.append(
                {
                    "field": f"{self.files_data_key}.default_preview",
                    "messages": e.messages,
                }
            )
