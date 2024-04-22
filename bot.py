#!/usr/bin/env python3

from datetime import datetime, timedelta
from typing import List
import typer
import requests
from pydantic import BaseModel, model_validator
import feedparser


app = typer.Typer()


class CTFModel(BaseModel):
    title: str
    link: str
    summary: str
    id: str
    guidislink: bool
    start_date: datetime
    finish_date: datetime
    logo_url: str
    href: str
    ctftime_url: str
    format: str
    format_text: str
    weight: float
    live_feed: str
    restrictions: str
    location: str
    onsite: bool
    organizers: str
    ctf_id: str
    ctf_name: str

    @model_validator(mode="before")
    def fix_start_date(cls, v):
        # parse 20240413T155959 as datetime
        v["start_date"] = datetime.strptime(v["start_date"], "%Y%m%dT%H%M%S")
        v["finish_date"] = datetime.strptime(v["finish_date"], "%Y%m%dT%H%M%S")
        return v


def parse_feed():
    res = feedparser.parse("https://ctftime.org/event/list/upcoming/rss/")
    entries = res.get("entries", [])
    m = [CTFModel.model_validate(entry) for entry in entries]
    return m


def gradient(weight: float) -> int:
    r = int(255 * (1 - weight))
    g = int(255 * (weight))
    b = 0x11
    out = r * (255**2) + g * 255 + b
    return out


@app.command()
def team_stats(webhook_url, team_id=279481):
    req = requests.get(
        f"https://ctftime.org/team/{team_id}", headers={"User-Agent": "Mozilla/5.0"}
    )
    req.raise_for_status()
    rating_overall = (
        req.content.split(b"Overall rating place:")[1]
        .split(b"</b>")[0]
        .split(b"<b>")[1]
        .strip()
    )
    country_rating = (
        req.content.split(b"Country place:")[1]
        .split(b'<a href="/stats/NO">')[1]
        .split(b"</a>")[0]
        .strip()
    )
    print(rating_overall)
    print(country_rating)

    r = requests.post(
        webhook_url,
        json={
            "content": "",
            "embeds": [
                {
                    "description": f"Rating:\n\nOverall: **{rating_overall.decode()}**\nCountry: **{country_rating.decode()}**",
                    "color": 0x00FFFF,
                },
            ],
        },
    )
    r.raise_for_status()


@app.command()
def discord(webhook_url):
    feeds = parse_feed()
    cutoff = datetime.now() + timedelta(days=7)
    embeds = []
    main = f"CTFs for {datetime.now().date()} -> {cutoff.now().date()}"
    weight_max = max(feeds, key=lambda f: f.weight).weight
    for feed in sorted(feeds, key=lambda f: f.weight, reverse=True):
        if feed.start_date < cutoff and not feed.onsite:
            embeds.append(
                {
                    "description": f"[{feed.title}]({feed.href})\nStarts: **<t:{int(feed.start_date.timestamp())}:R>**\nFormat: **{feed.format_text}**\nWeight: **{feed.weight}**",
                    "color": gradient(feed.weight / weight_max),
                    # "image": {
                    #     "url": "https://ctftime.org" + feed.logo_url,
                    #     "height": 10,
                    #     "width": 10,
                    # },
                }
            )
            print(feed.title, feed.weight, feed.href, feed.start_date, feed.finish_date)

    r = requests.post(
        webhook_url,
        json={
            "content": "",
            "embeds": embeds,
        },
    )
    r.raise_for_status()
    team_stats(webhook_url)


if __name__ == "__main__":
    app()
