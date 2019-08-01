# Search image (url)

Searches for similar images by the image returned by a GET request to the given URL.

**URL** : `/api/search?url=<image link>`

**Method** : `GET`

## Success Response

**Condition** : Image is valid.

**Code** : `200 OK`

**Content example**
```json
[
    {
        "post": {
            "id": 1341099,
            "user": "OberAsi",
            "created": "2016-05-28T13:08:25",
            "is_sfw": true,
            "is_nsfw": false,
            "is_nsfl": false,
            "image": "2016/05/28/1843282e59d4ce99.jpg",
            "thumb": "2016/05/28/1843282e59d4ce99.jpg"
        },
        "similarity": 0
    },
    {
        "post": {
            "id": 689360,
            "user": "copacabana",
            "created": "2015-03-15T16:30:08",
            "is_sfw": true,
            "is_nsfw": false,
            "is_nsfl": false,
            "image": "2015/03/15/46de10cfb3037b03.jpg",
            "thumb": "2015/03/15/46de10cfb3037b03.jpg"
        },
        "similarity": 234.20289611816406
    }
]
```

## Error Responses

**Condition** : If there was no url or the supplied url yields no response".

**Code** : `400 BAD REQUEST`

**Content** :
```json
{
    "error": "url is invalid""
}
```
```json
{
    "error": "url parameter missing""
}
```
## Notes

The similarity is currently the euclidian distance from the query image feature to the found image feature.
The smaller the value, the more alike they are. A similarity of `0` does not have to mean, that the images
are equal.