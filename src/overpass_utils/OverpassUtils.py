import overpy


class OverpassUtils:
    @staticmethod
    def get_route_latlng_list(
        route_num: str,
    ) -> tuple[list[tuple], list[dict]]:

        api = overpy.Overpass()
        query = f"""
            [out:json][timeout:25];
            area["name"="Colombo"]->.searchArea;
            (
            relation["type"="route"]["route"="bus"]["ref"="{route_num}"](area.searchArea);
            );
            out body;
            >;
            out body qt;
        """

        result = api.query(query)

        latlng_list = []
        for relation in result.relations:
            for member in relation.members:
                obj = member.resolve()
                if isinstance(obj, overpy.Way):
                    for node in obj.nodes:
                        latlng_list.append((float(node.lat), float(node.lon)))

        return latlng_list
