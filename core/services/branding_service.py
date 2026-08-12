from academics.models import SchoolSettings


class BrandingService:

    @staticmethod
    def settings(school):

        return SchoolSettings.load(school)