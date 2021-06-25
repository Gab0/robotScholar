
import indra.literature.pmc_client as pmc_client


def get_nxml(pmc_id):
    xml_str = pmc_client.get_xml(pmc_id)
    fname = pmc_id + '.nxml'
    with open(fname, 'wb') as fh:
        fh.write(xml_str.encode('utf-8'))
