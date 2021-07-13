"""
Unifies a GenericModule object with it's Dashboards
"""
import json
import os
from typing import Dict, Optional


def find_dashboard_by_id(pack_path: str, dashboard_id: str) -> Optional[Dict]:
    """
    Search for dashboard with the given id in the given pack path.

    Args:
        pack_path: a pack to search in
        dashboard_id: dashboard id to search for

    Returns: if found - the content of the dashboard, else - None.
    """
    for file_name in os.listdir(pack_path):
        file_path = os.path.join(pack_path, file_name)  # TODO: need to make sure how exactly the dashboards located in the pack
        if file_path.endswith('.json') and file_name.startswith('dashboard'): # it's a dashboard
            with open(file_path) as f:
                dashboard = json.load(f)
            if dashboard.get('id') == dashboard_id: # dashboard was found
                return dashboard
    return None


def insert_dashboards_to_generic_module(generic_module_path: str) -> Dict:
    """
    Unifies a GenericModule object with it's Dashboards
    Args:
        generic_module_path: a path to a GenericModule file (json)

    Returns: the unified GenericModule

    """
    pack_path = f'{os.path.dirname(os.path.dirname(generic_module_path))}/'
    pack_name = os.path.basename(pack_path.rstrip('/'))

    with open(generic_module_path) as f:
        generic_module = json.load(f)

    if views := generic_module.get('views'):
        for view in views:
            if tabs := view.get('tabs'):
                for tab in tabs:
                    if dashboard := tab.get('dashboard'):
                        dashboard_id = dashboard.get('id')
                        if dashboard_id:  # search dashboard in the GenericModule's pack
                            dashboard_content = find_dashboard_by_id(pack_path=pack_path, dashboard_id=dashboard_id)
                            if dashboard_content:
                                tab['dashboard'] = dashboard_content  # TODO: need to check its working
                            else:
                                print(f'Dashboard {dashboard_id} was not found in pack: {pack_name} '
                                      f'and therefore was not unified')

    else:  # there isn't a 'views' key in the genericModule json
        print('error')  # TODO: handle this - decide how we want to handle errors in the genericsModule raising exception maybe

    return generic_module
