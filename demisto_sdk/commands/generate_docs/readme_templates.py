SYSLOG = (
    "\n# %%UPDATE%% <Product Name>\nThis pack includes Cortex XSIAM content.\n\n\n## Configuration on Server "
    "Side\n%%UPDATE%% <Add vendor's specifications>\n\n## Collect Events from Vendor\nIn order to use the "
    "collector, use the [Broker VM](#broker-vm) option.\n\n\n### Broker VM\nTo create or configure the Broker VM, "
    "use the information described [here](https://docs-cortex.paloaltonetworks.com/r/Cortex-XDR/Cortex-XDR-Pro"
    "-Administrator-Guide/Configure-the-Broker-VM).\n\nYou can configure the specific vendor and product for this "
    "instance.\n\n1. Navigate to **Settings** > **Configuration** > **Data Broker** > **Broker VMs**. \n2. Go to the "
    "apps tab and add the **Syslog** app. If it already exists, click the **Syslog** app and then click "
    "**Configure**.\n3. Click **Add New**.\n4. When configuring the Syslog Collector, set the following values **(not "
    "relevant for CEF and LEEF formats)**:\n   - vendor as vendor - %%UPDATE%% <vendor>\n   - product as "
    "product - %%UPDATE%% <product>\n "
)

HTTP_COLLECTOR = (
    "\n# %%UPDATE%% <Product Name>\nThis pack includes Cortex XSIAM content.\n\n### Collect Events from %%UPDATE%% "
    "<product> (XSIAM)\n%%UPDATE%% <General specifications>\n\n**On XSIAM:**\n\n1. Navigate to **Settings** -> **Data "
    "Sources** -> **Add Data Source**.\n2. From the Type dropdown list, select Custom Integrations.\n3. Click "
    "**Custom - HTTP based Collector**.\n4. Click **Connect**.\n5. Set the following values:\n   - Name as "
    "%%UPDATE%%``\n   - Compression as %%UPDATE%%``\n   - Log Format as %%UPDATE%%``\n   - Vendor as %%UPDATE%%``\n   "
    "- Product as %%UPDATE%%``\n6. Creating a new HTTP Log Collector will allow you to generate a unique token, "
    "please save it since it will be used later.\n7. Click the 3 dots sign next to the newly created instance and "
    "copy the API Url, it will also be used later.\n\n**On %%UPDATE%% <product>:**\n\n %%UPDATE%% <reference to "
    "docs>\n\n<u>Guidelines:</u>\n1. \n "
)

XDRC = (
    "\n# %%UPDATE%% <Product Name>\nThis pack includes Cortex XSIAM content.\n\n\n## Configuration on Server "
    "Side\n %%UPDATE%% <Add vendor's specifications>\n\n## Collect Events from Vendor\nIn order to use the "
    "collector, use the [XDRC (XDR Collector)](#xdrc-xdr-collector) option.\n\n\n### XDRC (XDR Collector)\nTo create "
    "or configure the Filebeat collector, use the information described [here]("
    "https://docs.paloaltonetworks.com/cortex/cortex-xdr/cortex-xdr-pro-admin/cortex-xdr-collectors/xdr-collector"
    "-datasets#id7f0fcd4d-b019-4959-a43a-40b03db8a8b2).\n\nYou can configure the vendor and product by replacing ["
    "vendor]\\_[product]\\_raw.\n\nWhen configuring the instance, you should use a YML file that configures the "
    "vendor and product.\n\n\n#### Filebeat Configuration File\nCopy and paste the following in the *Filebeat "
    "Configuration File* section (inside the relevant profile under the *XDR Collectors "
    "Profiles*).\n\n```\n<%%UPDATE%% Add here the filebeat>\n```\n "
)

README_TEMPLATES = {"syslog": SYSLOG, "http-collector": HTTP_COLLECTOR, "xdrc": XDRC}
