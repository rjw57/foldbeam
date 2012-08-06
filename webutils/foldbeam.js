var foldbeam = {
    url_root: 'http://localhost:8888/',

    utils: {
        getParameterByName: function(name) {
            var match = RegExp('[?&]' + name + '=([^&]*)')
                .exec(window.location.search);
            return match && decodeURIComponent(match[1].replace(/\+/g, ' '));
        },
    },

    ResourceCollection: function(cls, url) {
        return {
            fetch: function() {
                var self = this;
                $.getJSON(url, function(data) {
                    self.resources = [];
                    for(idx in data.resources) {
                        self.resources[idx] = cls(data.resources[idx].url);
                    }
                    self._is_loaded = true;
                    self.ready();
                });
                return this;
            },

            ready: function(func) {
                if(func === undefined) {
                    this._on_ready();
                } else {
                    this._on_ready = func;
                    if(this._is_loaded) { this.ready(); }
                }
                return this;
            },
            _on_ready: function() { },
            _is_loaded: false,

            resources: [],
        }.fetch();
    },

    User: function(url) {
        return {
            fetch: function() {
                var self = this;
                $.getJSON(url, function(data) {
                    self.username = data.username;
                    self.maps = foldbeam.ResourceCollection(foldbeam.Map, data.resources.maps.url);
                    self.layers = foldbeam.ResourceCollection(foldbeam.Layer, data.resources.layers.url);
                    self.buckets = foldbeam.ResourceCollection(foldbeam.Bucket, data.resources.buckets.url);
                    self._is_loaded = true;
                    self.ready();
                });
                return this;
            },

            ready: function(func) {
                if(func === undefined) {
                    this._on_ready();
                } else {
                    this._on_ready = func;
                    if(this._is_loaded) { this.ready(); }
                }
                return this;
            },
            _on_ready: function() { },
            _is_loaded: false,
        }.fetch();
    },

    Map: function(url) {
        return {
            fetch: function() {
                var self = this;
                $.getJSON(url, function(data) {
                    self.extent = data.extent;
                    self.layer_tiles = data.layer_tiles;
                    self.name = data.name;
                    self.srs = data.srs;

                    self._is_loaded = true;
                    self.ready();
                });
                return this;
            },

            ready: function(func) {
                if(func === undefined) {
                    this._on_ready();
                } else {
                    this._on_ready = func;
                    if(this._is_loaded) { this.ready(); }
                }
                return this;
            },
            _on_ready: function() { },
            _is_loaded: false,
        }.fetch();
    },

    Layer: function(url) {
        return {
            fetch: function() {
                var self = this;
                $.getJSON(url, function(data) {
                    self.name = data.name;
                    self._is_loaded = true;
                    self.ready();
                });
                return this;
            },

            ready: function(func) {
                if(func === undefined) {
                    this._on_ready();
                } else {
                    this._on_ready = func;
                    if(this._is_loaded) { this.ready(); }
                }
                return this;
            },
            _on_ready: function() { },
            _is_loaded: false,
        }.fetch();
    },

    Bucket: function(url) {
        return {
            fetch: function() {
                var self = this;
                $.getJSON(url, function(data) {
                    self.name = data.name;
                    self._is_loaded = true;
                    self.ready();
                });
                return this;
            },

            ready: function(func) {
                if(func === undefined) {
                    this._on_ready();
                } else {
                    this._on_ready = func;
                    if(this._is_loaded) { this.ready(); }
                }
                return this;
            },
            _on_ready: function() { },
            _is_loaded: false,
        }.fetch();
    },

    get_user: function(username) {
        return new foldbeam.User(foldbeam.url_root + username);
    },
};
