from app.watch.diff import ResourceSnapshot, compute_resource_diff


def _snap(resource_type, native_id, **attrs):
    return ResourceSnapshot(resource_type=resource_type, native_id=native_id, attributes=attrs)


def test_detects_added_resource():
    previous = []
    current = [_snap("network", "vpc-1", name="prod")]
    diff = compute_resource_diff(previous, current)

    assert len(diff) == 1
    assert diff[0].change_type == "added"
    assert diff[0].native_id == "vpc-1"


def test_detects_removed_resource():
    previous = [_snap("network", "vpc-1", name="prod")]
    current = []
    diff = compute_resource_diff(previous, current)

    assert len(diff) == 1
    assert diff[0].change_type == "removed"


def test_detects_modified_resource():
    previous = [_snap("security_group", "sg-1", rules=["22/tcp from 10.0.0.0/8"])]
    current = [_snap("security_group", "sg-1", rules=["22/tcp from 0.0.0.0/0"])]
    diff = compute_resource_diff(previous, current)

    assert len(diff) == 1
    assert diff[0].change_type == "modified"
    assert diff[0].previous_attributes["rules"] == ["22/tcp from 10.0.0.0/8"]
    assert diff[0].current_attributes["rules"] == ["22/tcp from 0.0.0.0/0"]


def test_no_diff_for_unchanged_resource():
    previous = [_snap("network", "vpc-1", name="prod")]
    current = [_snap("network", "vpc-1", name="prod")]
    diff = compute_resource_diff(previous, current)
    assert diff == []


def test_same_native_id_different_resource_type_treated_independently():
    previous = [_snap("network", "shared-id", name="net")]
    current = [_snap("subnet", "shared-id", name="subnet")]
    diff = compute_resource_diff(previous, current)

    change_types = {(d.resource_type, d.change_type) for d in diff}
    assert ("network", "removed") in change_types
    assert ("subnet", "added") in change_types
