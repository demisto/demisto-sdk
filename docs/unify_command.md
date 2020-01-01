### Unify

Unify the code, image and description files to a single Demisto yaml file.
**Arguments**:
* *-i INDIR, --indir INDIR*
  The path to the directory in which the files reside
* *-o OUTDIR, --outdir OUTDIR*
  The path to the directory into which to write the unified yml file

**Examples**:
`demisto-sdk unify -i Integrations/MyInt -o Integrations`
This will grab the integration components in "Integrations/MyInt" directory and unify them to a single yaml file
that will be created in the "Integrations" directory.
