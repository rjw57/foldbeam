Design notes
============

Compositing pipeline is nodal. Rendering is a pull operation where a geographic region is requested on an output and a
Node is expected to fulfil the requirements.

An edge therefore consists of an endpoint from which pulled and an input through which 'damage' events can be pushed.

The overall effect is something like the following:

.. graphviz::

    digraph g {
        rankdir=LR;
        node [
            shape=rectangle
        ];
        "Raster Source" -> "Render Raster" -> "Display";
        "Vector Source" -> "Render Vector" -> "Display";
    }

Map files
---------

.. literalinclude:: map_example.yaml
    :language: yaml
    :linenos:

Web GUI
-------

.. figure:: viewer-mockup.png
    :width: 100%

    An example design for the map viewer GUI.

Architecture
------------

The overall system needs to be architectured to pass the 'Range Rover test' whereby a hypothetical deployment works like
this:

1. The office/cloud has the overall foldbeam database.

2. Subsets of this database are synchronised to a laptop.

3. This laptop acts as the 'field hub' out on a dig.

4. Handheld devices join an ad hoc network in the field.

5. Data capture happens on a device. Data is transparently streamed to the foldbeam laptop.

6. On returning to the office data is transparently streamed to the office/cloud.

The data model has the concept of a 'bucket' of features. A bucket contains metadata about creator, location, project,
etc. The bucket is itself a collection of features which may be of any type (line, polygon, point, etc). Each bucket is
a single database which may be transparently sychronised online a la CouchDB.

Once gathered, buckets may be filtered, combined and processed in a non-destructive fashion.

Each bucket has a UUID as does each feature within the bucket. Said UUID can be used to determine a unique URN for a
feature or bucket.

An example of use: in the field a device maintains a set of buckets which may be updated individually. The device
advertises these buckets via UPnP for syncing. Buckets may contain features which are themselves references to other
buckets or to procedures for generating features from a bucket.

A database must be complete: any buckets referenced by URN must have a record in the database. This record *could* be a
reference to another database.

Crucially the bucket data store should be cacheable: it should be trivial to determine if a cache is in sync with a
bucket and it should be possible to incrementally update the cache. The idea is that one could, for example, use a
CouchDB with GeoJSON documents for data storage and PostGIS for indexed retrieval for rendering. The PostGIS database
should be created and updated on demand.

One possible data flow would be the following:

.. figure:: architecture.png
    :width: 100%

    A possible data flow for the foldbeam system.

Thoughts
````````

The most obvious synchronisation protocol is CouchDB's wire protocol. It has the advantage of being HTTP-based, REST-ful
and proven. If one is to use CouchDB, one might as well use GeoJSON or a superset as a feature description.

For example, using CouchDB the following document could describe a bucket:

.. code-block:: javascript

    {
        "_id": "<unique id>",
        "type": "foldbeam.bucket",
        "urn": "urn:foldbeam:bucket:<id>",
        "metadata": {
            // whatever metadata the user wishes to use
        },
    }

A feature within a bucket would look like this:

.. code-block:: javascript

    {
        "_id": "<unique id>",
        "type": "foldbeam.bucket.feature",
        "urn": "urn:foldbeam:bucket.feature:<id>",
        "bucket": "<bucket id>",
        "feature": {
            // GeoJSON feature
        },
        "metadata": {
            // whatever metadata the user wishes to use
        },
    }

This approach allows for single-bucket databases as a special case of many buckets in one database. In addition features
may reference other buckets in other databases or may specify a filtering/mapping operation but the way this is to be
achieved needs to be thought through carefully.

A device may advertise bucket databases via UPnP. Synchronisation is two-way. Database synchronisation is an
all-or-nothing affair. Merging buckets together is dove via bucket references/URNs.

A key concept of buckets is that, due to them being cacheable and incrementally updatable, they can have a view on
themselves appropriate for the use case. For example, a transparent copy of a bucket's features can be maintained in a
PostGIS table by a monitoring process. The PostGIS table will be eventually consistent with the CouchDB bucket.

Conflict resolution is *only* performed by the CouchDB resolution system. All other views let the CouchDB store 'win'.
