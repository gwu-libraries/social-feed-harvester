"""
A fetchable retrieves some resource and returns the appropriate WARC records.

It may also:
* Parse the resource and to extract links to additional resources and submit for retrieval.
* Get/set harvest state for resources that are incrementally harvested.
* Add to the list of fetched resources to avoid refetching.

A fetchable should implement the signature of resource.Resource.  This includes the class variables:
* is_fetchable: indicating whether fetching the resource is supported.
* hostname: the hostname of the resource to be fetched, to be used for determining delays.
"""