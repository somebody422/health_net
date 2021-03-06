from django.conf.urls import url

from . import views

urlpatterns = [
# Miscellaneous ****************************************************************
    url(r'^$', views.index, name='index'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^dashboard/$', views.dashboard, name='dashboard'),
# Register *********************************************************************
    url(r'^register_1/$', views.register_step_1, name='register_1'),
    url(r'^register_2/$', views.register_step_2, name='register_2'),
    url(r'^register_2-5/$', views.more_register, name='more_register'),
    url(r'^register_3/$', views.register_step_3, name='register_3'),
    url(r'^register_finish/$', views.register_finish, name='register_finish'),
    url(r'^register_doctor/$', views.register_doctor, name='register_doctor'),
    url(r'^register_nurse/$', views.register_nurse, name='register_nurse'),
    url(r'^register_admin/$', views.register_admin, name='register_admin'),
    url(r'^register_admin_begin/$', views.register_admin_begin, name='register_admin_begin'),
    url(r'^make_hospital/$', views.make_hospital, name='make_hospital'),
# Profile **********************************************************************
    url(r'^profile/$', views.profile_redirect, name='profile_redirect'),
    url(r'^profile/(?P<id>[0-9]+)/$', views.profile, name='profile'),
    url(r'^profile/(?P<id>[0-9]+)/edit/$', views.profile_edit, name='profile_edit'),
# Calendar *********************************************************************
    url(r'^calendar/$', views.calendar, name='calendar'),
    url(r'^calendar_feed/$', views.calendar_feed, name='calendar_feed'),
    url(r'^appointment/create/$', views.create_appt, name='create_appt'),
    url(r'^appointment/view/(?P<id>[0-9]+)/$', views.view_appt, name='view_appt'),
    url(r'^appointment/delete/(?P<id>[0-9]+)/$', views.delete_appt, name='delete_appt'),
# Prescription *****************************************************************
    url(r'^prescription/create/$', views.create_prescription, name='create_prescription'),
    url(r'^prescription/view/(?P<id>[0-9]+)/$', views.view_prescriptions, name='view_prescriptions'),
    url(r'^register_medication/$', views.register_medication, name='register_medication'),
# Tests & Records **************************************************************
    url(r'^medrec/$', views.view_medrec, name='view_medrec'),
    url(r'^medrec/(?P<id>[0-9]+)/$', views.view_medrec_by_id, name='view_medrec_by_id'),
    url(r'^create_test/$', views.create_test, name='create_test'),
# Logging **********************************************************************
    url(r'^logs/$', views.logging, name='logging'),
    url(r'^system_statistics/$', views.view_system_statistics, name='systemstatistics'),
# Admission / Discharge ********************************************************
    url(r'create_admission/$', views.create_admission, name='create_admission'),
    url(r'delete_admission/(?P<id>[0-9]+)/$', views.delete_admission, name='delete_admission'),
# Transfer *********************************************************************
    url(r'^transfer_request/$', views.transfer_request, name='transfer_request'),
    url(r'^transfer_view/(?P<id>[0-9]+)/$', views.transfer_view, name='transfer_view'),
# Messages *********************************************************************
    url(r'^inbox/$', views.inbox, name='inbox'),
    url(r'^message_send/$', views.message_send, name='message_send'),
    url(r'^message_view/(?P<id>[0-9]+)/$', views.message_view, name='message_view'),
# Export ***********************************************************************
    url(r'^jexport/$', views.jexport, name='jexport'),
    url(r'^jimport/$', views.jimport, name='jimport')
]
