from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import MULTIPART_CONTENT

from taiga.base.utils import json

from taiga.permissions.permissions import MEMBERS_PERMISSIONS, ANON_PERMISSIONS, USER_PERMISSIONS
from taiga.projects.attachments.serializers import AttachmentSerializer

from tests import factories as f
from tests.utils import helper_test_http_method
from tests.utils import helper_test_http_method_and_count
from tests.utils import disconnect_signals
from tests.utils import reconnect_signals

import pytest
pytestmark = pytest.mark.django_db


def setup_module(module):
    disconnect_signals()


def teardown_module(module):
    reconnect_signals()


@pytest.fixture
def data():
    m = type("Models", (object,), {})

    m.registered_user = f.UserFactory.create()
    m.project_member_with_perms = f.UserFactory.create()
    m.project_member_without_perms = f.UserFactory.create()
    m.project_owner = f.UserFactory.create()
    m.other_user = f.UserFactory.create()

    m.public_project = f.ProjectFactory(is_private=False,
                                        anon_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                                        public_permissions=list(map(lambda x: x[0], USER_PERMISSIONS)),
                                        owner=m.project_owner)
    m.private_project1 = f.ProjectFactory(is_private=True,
                                          anon_permissions=list(map(lambda x: x[0], ANON_PERMISSIONS)),
                                          public_permissions=list(map(lambda x: x[0], USER_PERMISSIONS)),
                                          owner=m.project_owner)
    m.private_project2 = f.ProjectFactory(is_private=True,
                                          anon_permissions=[],
                                          public_permissions=[],
                                          owner=m.project_owner)

    m.public_membership = f.MembershipFactory(project=m.public_project,
                                          user=m.project_member_with_perms,
                                          role__project=m.public_project,
                                          role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    m.private_membership1 = f.MembershipFactory(project=m.private_project1,
                                                user=m.project_member_with_perms,
                                                role__project=m.private_project1,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    f.MembershipFactory(project=m.private_project1,
                        user=m.project_member_without_perms,
                        role__project=m.private_project1,
                        role__permissions=[])
    m.private_membership2 = f.MembershipFactory(project=m.private_project2,
                                                user=m.project_member_with_perms,
                                                role__project=m.private_project2,
                                                role__permissions=list(map(lambda x: x[0], MEMBERS_PERMISSIONS)))
    f.MembershipFactory(project=m.private_project2,
                        user=m.project_member_without_perms,
                        role__project=m.private_project2,
                        role__permissions=[])

    f.MembershipFactory(project=m.public_project,
                        user=m.project_owner,
                        is_owner=True)

    f.MembershipFactory(project=m.private_project1,
                        user=m.project_owner,
                        is_owner=True)

    f.MembershipFactory(project=m.private_project2,
                        user=m.project_owner,
                        is_owner=True)

    return m

@pytest.fixture
def data_us(data):
    m = type("Models", (object,), {})
    m.public_user_story = f.UserStoryFactory(project=data.public_project, ref=1)
    m.public_user_story_attachment = f.UserStoryAttachmentFactory(project=data.public_project,
                                                                  content_object=m.public_user_story)
    m.private_user_story1 = f.UserStoryFactory(project=data.private_project1, ref=5)
    m.private_user_story1_attachment = f.UserStoryAttachmentFactory(project=data.private_project1,
                                                                    content_object=m.private_user_story1)
    m.private_user_story2 = f.UserStoryFactory(project=data.private_project2, ref=9)
    m.private_user_story2_attachment = f.UserStoryAttachmentFactory(project=data.private_project2,
                                                                    content_object=m.private_user_story2)
    return m

@pytest.fixture
def data_task(data):
    m = type("Models", (object,), {})
    m.public_task = f.TaskFactory(project=data.public_project, ref=2)
    m.public_task_attachment = f.TaskAttachmentFactory(project=data.public_project, content_object=m.public_task)
    m.private_task1 = f.TaskFactory(project=data.private_project1, ref=6)
    m.private_task1_attachment = f.TaskAttachmentFactory(project=data.private_project1, content_object=m.private_task1)
    m.private_task2 = f.TaskFactory(project=data.private_project2, ref=10)
    m.private_task2_attachment = f.TaskAttachmentFactory(project=data.private_project2, content_object=m.private_task2)
    return m

@pytest.fixture
def data_issue(data):
    m = type("Models", (object,), {})
    m.public_issue = f.IssueFactory(project=data.public_project, ref=3)
    m.public_issue_attachment = f.IssueAttachmentFactory(project=data.public_project, content_object=m.public_issue)
    m.private_issue1 = f.IssueFactory(project=data.private_project1, ref=7)
    m.private_issue1_attachment = f.IssueAttachmentFactory(project=data.private_project1, content_object=m.private_issue1)
    m.private_issue2 = f.IssueFactory(project=data.private_project2, ref=11)
    m.private_issue2_attachment = f.IssueAttachmentFactory(project=data.private_project2, content_object=m.private_issue2)
    return m

@pytest.fixture
def data_wiki(data):
    m = type("Models", (object,), {})
    m.public_wiki = f.WikiPageFactory(project=data.public_project, slug=4)
    m.public_wiki_attachment = f.WikiAttachmentFactory(project=data.public_project, content_object=m.public_wiki)
    m.private_wiki1 = f.WikiPageFactory(project=data.private_project1, slug=8)
    m.private_wiki1_attachment = f.WikiAttachmentFactory(project=data.private_project1, content_object=m.private_wiki1)
    m.private_wiki2 = f.WikiPageFactory(project=data.private_project2, slug=12)
    m.private_wiki2_attachment = f.WikiAttachmentFactory(project=data.private_project2, content_object=m.private_wiki2)
    return m

def test_user_story_attachment_retrieve(client, data, data_us):
    public_url = reverse('userstory-attachments-detail', kwargs={"pk": data_us.public_user_story_attachment.pk})
    private_url1 = reverse('userstory-attachments-detail', kwargs={"pk": data_us.private_user_story1_attachment.pk})
    private_url2 = reverse('userstory-attachments-detail', kwargs={"pk": data_us.private_user_story2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'get', public_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url1, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url2, None, users)
    assert results == [401, 403, 403, 200, 200]


def test_task_attachment_retrieve(client, data, data_task):
    public_url = reverse('task-attachments-detail', kwargs={"pk": data_task.public_task_attachment.pk})
    private_url1 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task1_attachment.pk})
    private_url2 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'get', public_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url1, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url2, None, users)
    assert results == [401, 403, 403, 200, 200]


def test_issue_attachment_retrieve(client, data, data_issue):
    public_url = reverse('issue-attachments-detail', kwargs={"pk": data_issue.public_issue_attachment.pk})
    private_url1 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue1_attachment.pk})
    private_url2 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'get', public_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url1, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url2, None, users)
    assert results == [401, 403, 403, 200, 200]


def test_wiki_attachment_retrieve(client, data, data_wiki):
    public_url = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.public_wiki_attachment.pk})
    private_url1 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki1_attachment.pk})
    private_url2 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method(client, 'get', public_url, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url1, None, users)
    assert results == [200, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'get', private_url2, None, users)
    assert results == [401, 403, 403, 200, 200]


def test_user_story_attachment_update(client, data, data_us):
    public_url = reverse("userstory-attachments-detail",
                         args=[data_us.public_user_story_attachment.pk])
    private_url1 = reverse("userstory-attachments-detail",
                           args=[data_us.private_user_story1_attachment.pk])
    private_url2 = reverse("userstory-attachments-detail",
                           args=[data_us.private_user_story2_attachment.pk])

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = AttachmentSerializer(data_us.public_user_story_attachment).data
    attachment_data["description"] = "test"

    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, "put", public_url, attachment_data, users)
    # assert results == [401, 403, 403, 400, 400]
    assert results == [405, 405, 405, 405, 405]

    results = helper_test_http_method(client, "put", private_url1, attachment_data, users)
    # assert results == [401, 403, 403, 400, 400]
    assert results == [405, 405, 405, 405, 405]

    results = helper_test_http_method(client, "put", private_url2, attachment_data, users)
    # assert results == [401, 403, 403, 400, 400]
    assert results == [405, 405, 405, 405, 405]


def test_task_attachment_update(client, data, data_task):
    public_url = reverse('task-attachments-detail', kwargs={"pk": data_task.public_task_attachment.pk})
    private_url1 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task1_attachment.pk})
    private_url2 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = AttachmentSerializer(data_task.public_task_attachment).data
    attachment_data["description"] = "test"
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'put', public_url, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'put', private_url1, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'put', private_url2, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]


def test_issue_attachment_update(client, data, data_issue):
    public_url = reverse('issue-attachments-detail', kwargs={"pk": data_issue.public_issue_attachment.pk})
    private_url1 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue1_attachment.pk})
    private_url2 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = AttachmentSerializer(data_issue.public_issue_attachment).data
    attachment_data["description"] = "test"
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'put', public_url, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'put', private_url1, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'put', private_url2, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]


def test_wiki_attachment_update(client, data, data_wiki):
    public_url = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.public_wiki_attachment.pk})
    private_url1 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki1_attachment.pk})
    private_url2 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = AttachmentSerializer(data_wiki.public_wiki_attachment).data
    attachment_data["description"] = "test"
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'put', public_url, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'put', private_url1, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'put', private_url2, attachment_data, users)
    assert results == [405, 405, 405, 405, 405]
    # assert results == [401, 403, 403, 200, 200]


def test_user_story_attachment_patch(client, data, data_us):
    public_url = reverse('userstory-attachments-detail', kwargs={"pk": data_us.public_user_story_attachment.pk})
    private_url1 = reverse('userstory-attachments-detail', kwargs={"pk": data_us.private_user_story1_attachment.pk})
    private_url2 = reverse('userstory-attachments-detail', kwargs={"pk": data_us.private_user_story2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test"}
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'patch', public_url, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url1, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url2, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]


def test_task_attachment_patch(client, data, data_task):
    public_url = reverse('task-attachments-detail', kwargs={"pk": data_task.public_task_attachment.pk})
    private_url1 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task1_attachment.pk})
    private_url2 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test"}
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'patch', public_url, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url1, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url2, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]


def test_issue_attachment_patch(client, data, data_issue):
    public_url = reverse('issue-attachments-detail', kwargs={"pk": data_issue.public_issue_attachment.pk})
    private_url1 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue1_attachment.pk})
    private_url2 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test"}
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'patch', public_url, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url1, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url2, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]


def test_wiki_attachment_patch(client, data, data_wiki):
    public_url = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.public_wiki_attachment.pk})
    private_url1 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki1_attachment.pk})
    private_url2 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test"}
    attachment_data = json.dumps(attachment_data)

    results = helper_test_http_method(client, 'patch', public_url, attachment_data, users)
    assert results == [401, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url1, attachment_data, users)
    assert results == [401, 200, 200, 200, 200]
    results = helper_test_http_method(client, 'patch', private_url2, attachment_data, users)
    assert results == [401, 403, 403, 200, 200]


def test_user_story_attachment_delete(client, data, data_us):
    public_url = reverse('userstory-attachments-detail', kwargs={"pk": data_us.public_user_story_attachment.pk})
    private_url1 = reverse('userstory-attachments-detail', kwargs={"pk": data_us.private_user_story1_attachment.pk})
    private_url2 = reverse('userstory-attachments-detail', kwargs={"pk": data_us.private_user_story2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
    ]

    results = helper_test_http_method(client, 'delete', public_url, None, users)
    assert results == [401, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private_url1, None, users)
    assert results == [401, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private_url2, None, users)
    assert results == [401, 403, 403, 204]


def test_task_attachment_delete(client, data, data_task):
    public_url = reverse('task-attachments-detail', kwargs={"pk": data_task.public_task_attachment.pk})
    private_url1 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task1_attachment.pk})
    private_url2 = reverse('task-attachments-detail', kwargs={"pk": data_task.private_task2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
    ]

    results = helper_test_http_method(client, 'delete', public_url, None, users)
    assert results == [401, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private_url1, None, users)
    assert results == [401, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private_url2, None, users)
    assert results == [401, 403, 403, 204]


def test_issue_attachment_delete(client, data, data_issue):
    public_url = reverse('issue-attachments-detail', kwargs={"pk": data_issue.public_issue_attachment.pk})
    private_url1 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue1_attachment.pk})
    private_url2 = reverse('issue-attachments-detail', kwargs={"pk": data_issue.private_issue2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
    ]

    results = helper_test_http_method(client, 'delete', public_url, None, users)
    assert results == [401, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private_url1, None, users)
    assert results == [401, 403, 403, 204]
    results = helper_test_http_method(client, 'delete', private_url2, None, users)
    assert results == [401, 403, 403, 204]


def test_wiki_attachment_delete(client, data, data_wiki):
    public_url = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.public_wiki_attachment.pk})
    private_url1 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki1_attachment.pk})
    private_url2 = reverse('wiki-attachments-detail', kwargs={"pk": data_wiki.private_wiki2_attachment.pk})

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
    ]

    results = helper_test_http_method(client, 'delete', public_url, None, [None, data.registered_user])
    assert results == [401, 204]
    results = helper_test_http_method(client, 'delete', private_url1, None, [None, data.registered_user])
    assert results == [401, 204]
    results = helper_test_http_method(client, 'delete', private_url2, None, users)
    assert results == [401, 403, 403, 204]

def test_user_story_attachment_create(client, data, data_us):
    url = reverse('userstory-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test",
                       "object_id": data_us.public_user_story_attachment.object_id,
                       "project": data_us.public_user_story_attachment.project_id,
                       "attached_file": SimpleUploadedFile("test.txt", b"test")}

    _after_each_request_hook = lambda: attachment_data["attached_file"].seek(0)

    results = helper_test_http_method(client, 'post', url, attachment_data, users,
                                      content_type=MULTIPART_CONTENT,
                                      after_each_request=_after_each_request_hook)
    assert results == [401, 403, 403, 201, 201]


def test_task_attachment_create(client, data, data_task):
    url = reverse('task-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test",
                       "object_id": data_task.public_task_attachment.object_id,
                       "project": data_task.public_task_attachment.project_id,
                       "attached_file": SimpleUploadedFile("test.txt", b"test")}

    _after_each_request_hook = lambda: attachment_data["attached_file"].seek(0)

    results = helper_test_http_method(client, 'post', url, attachment_data, users,
                                      content_type=MULTIPART_CONTENT,
                                      after_each_request=_after_each_request_hook)
    assert results == [401, 403, 403, 201, 201]


def test_issue_attachment_create(client, data, data_issue):
    url = reverse('issue-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test",
                       "object_id": data_issue.public_issue_attachment.object_id,
                       "project": data_issue.public_issue_attachment.project_id,
                       "attached_file": SimpleUploadedFile("test.txt", b"test")}

    _after_each_request_hook = lambda: attachment_data["attached_file"].seek(0)

    results = helper_test_http_method(client, 'post', url, attachment_data, users,
                                      content_type=MULTIPART_CONTENT,
                                      after_each_request=_after_each_request_hook)

    assert results == [401, 403, 403, 201, 201]


def test_wiki_attachment_create(client, data, data_wiki):
    url = reverse('wiki-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    attachment_data = {"description": "test",
                       "object_id": data_wiki.public_wiki_attachment.object_id,
                       "project": data_wiki.public_wiki_attachment.project_id,
                       "attached_file": SimpleUploadedFile("test.txt", b"test")}

    _after_each_request_hook = lambda: attachment_data["attached_file"].seek(0)

    results = helper_test_http_method(client, 'post', url, attachment_data, users,
                                      content_type=MULTIPART_CONTENT,
                                      after_each_request=_after_each_request_hook)

    assert results == [401, 201, 201, 201, 201]


def test_user_story_attachment_list(client, data, data_us):
    url = reverse('userstory-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method_and_count(client, 'get', url, None, users)
    assert results == [(200, 2), (200, 2), (200, 2), (200, 3), (200, 3)]


def test_task_attachment_list(client, data, data_task):
    url = reverse('task-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method_and_count(client, 'get', url, None, users)
    assert results == [(200, 2), (200, 2), (200, 2), (200, 3), (200, 3)]


def test_issue_attachment_list(client, data, data_issue):
    url = reverse('issue-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method_and_count(client, 'get', url, None, users)
    assert results == [(200, 2), (200, 2), (200, 2), (200, 3), (200, 3)]


def test_wiki_attachment_list(client, data, data_wiki):
    url = reverse('wiki-attachments-list')

    users = [
        None,
        data.registered_user,
        data.project_member_without_perms,
        data.project_member_with_perms,
        data.project_owner
    ]

    results = helper_test_http_method_and_count(client, 'get', url, None, users)
    assert results == [(200, 2), (200, 2), (200, 2), (200, 3), (200, 3)]
