function podcastApp() {
  return {
    feed: null,
    playlist: null,
    loading: true,
    error: null,
    audio: new Audio(),
    currentEpisodeIndex: -1,
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    progress: 0,

    get currentEpisode() {
      console.log("currentEpisode", this.currentEpisodeIndex);
      return this.currentEpisodeIndex >= 0 && this.feed?.items
        ? this.feed.items[this.currentEpisodeIndex]
        : null;
    },
    getPlaylistIdFromUrl() {
      let pattern = /\/playlists\/(.+)/i;
      let playlistId = window.location.pathname.match(pattern)[1];
      return playlistId;
    },
    init() {
      this.fetchPodcast();

      // Set up audio event listeners
      this.audio.addEventListener("timeupdate", () => {
        this.currentTime = this.audio.currentTime;
        this.duration = this.audio.duration || 0;
        this.progress = (this.currentTime / this.duration) * 100 || 0;
      });

      this.audio.addEventListener("ended", () => {
        this.nextTrack();
      });

      this.audio.addEventListener("play", () => {
        this.isPlaying = true;
      });

      this.audio.addEventListener("pause", () => {
        this.isPlaying = false;
      });
    },

    async fetchPodcast() {
      try {
        this.loading = true;
        const response = await fetch("feed.json");

        if (!response.ok) {
          throw new Error("Failed to fetch feed");
        }

        this.feed = await response.json();
        this.loading = false;
      } catch (err) {
        this.error = err.message;
        this.loading = false;
      }
    },
    getArtists(track) {
      // get the artists of the track
      let artists = track.artists.map((artist) => artist.name).join(", ");
      return artists;
    },
    setTitle() {
      // set the title of the window to the Emoji speaker symbol and the title of the track
      console.log("setTitle");
      if (this.currentEpisode) {
        document.title = `🔊 ${this.currentEpisode.artists[0].name} — ${this.currentEpisode.name}`;
      } else {
        document.title = this.playlist.name;
      }
    },
    setMediaSession() {
      if (!"mediaSession" in navigator) return;

      navigator.mediaSession.metadata = new MediaMetadata({
        title: this.currentEpisode.title,
        artist: this.feed.title,
        album: this.feed.title,
        artwork: [
          {
            src: this.currentEpisode.image,
            sizes: "96x96",
            type: "image/png",
          },
          {
            src: this.currentEpisode.image,
            sizes: "128x128",
            type: "image/png",
          },
          {
            src: this.currentEpisode.image,
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: this.currentEpisode.image,
            sizes: "256x256",
            type: "image/png",
          },
          {
            src: this.currentEpisode.image,
            sizes: "384x384",
            type: "image/png",
          },
          {
            src: this.currentEpisode.image,
            sizes: "512x512",
            type: "image/png",
          },
        ],
      });

      navigator.mediaSession.setActionHandler("play", () => this.audio.play());
      navigator.mediaSession.setActionHandler("pause", () =>
        this.audio.pause()
      );
      navigator.mediaSession.setActionHandler("previoustrack", () =>
        this.previousTrack()
      );
      navigator.mediaSession.setActionHandler("nexttrack", () =>
        this.nextTrack()
      );
      navigator.mediaSession.setActionHandler("seekto", (details) => {
        if (details.seekTime) {
          this.audio.currentTime = details.seekTime;
        } else {
          // If no seekTime is provided, we can use the current time
          this.audio.currentTime = this.audio.currentTime;
        }
      });
    },
    async playEpisode(index) {
      if (index === this.currentEpisodeIndex && this.isPlaying) {
        this.audio.pause();
        return;
      }

      if (index !== this.currentEpisodeIndex) {
        this.currentEpisodeIndex = index;

        try {
          this.setMediaSession();
          // this.setTitle();
          this.audio.pause();

          const episode = this.feed.items[this.currentEpisodeIndex];
          console.log("episode", episode);
          console.log("episode.attachments", episode.attachments);
          const audioUrl = episode.attachments[0].url;
          console.log("episode", episode);
          this.audio.src = audioUrl;
          this.audio.load();
        } catch (err) {
          console.error("Error loading track:", err);
          return;
        }
      }

      this.audio.play();
    },

    togglePlayPause(index) {
      if (index !== undefined && index !== this.currentEpisodeIndex) {
        this.playEpisode(index);
        return;
      }

      if (
        this.currentEpisodeIndex === -1 &&
        this.playlist?.tracks?.length > 0
      ) {
        this.playEpisode(0);
        return;
      }

      if (this.isPlaying) {
        this.audio.pause();
      } else {
        this.audio.play();
      }
    },

    nextTrack() {
      this.audio.pause();
      if (!this.feed?.item?.length) return;
      const nextIndex = (this.currentEpisodeIndex + 1) % this.feed.items.length;
      this.playEpisode(nextIndex);
    },

    previousTrack() {
      if (!this.playlist?.tracks?.length) return;

      const prevIndex =
        this.currentEpisodeIndex <= 0
          ? this.playlist.tracks.length - 1
          : this.currentEpisodeIndex - 1;

      this.playEpisode(prevIndex);
    },

    seek(event) {
      const container = event.currentTarget;
      const rect = container.getBoundingClientRect();
      const clickPosition = (event.clientX - rect.left) / rect.width;

      if (this.audio && this.audio.duration) {
        this.audio.currentTime = clickPosition * this.audio.duration;
      }
    },

    formatTime(seconds) {
      if (isNaN(seconds) || seconds === Infinity) return "0:00";

      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60)
        .toString()
        .padStart(2, "0");
      return `${mins}:${secs}`;
    },
  };
}
