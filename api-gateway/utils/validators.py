from marshmallow import Schema, fields, validates, ValidationError
import re


class CreatePostSchema(Schema):
    title = fields.String(required=True)
    description = fields.String(required=True)
    is_private = fields.Boolean(default=False)
    tags = fields.List(fields.String(), default=[])

    @validates("title")
    def validate_title(self, value):
        if len(value) < 3 or len(value) > 255:
            raise ValidationError("Title must be between 3 and 255 characters")

    @validates("description")
    def validate_description(self, value):
        if len(value) < 10 or len(value) > 2000:
            raise ValidationError("Description must be between 10 and 2000 characters")

    @validates("tags")
    def validate_tags(self, value):
        if len(value) > 10:
            raise ValidationError("Maximum 10 tags allowed")

        for tag in value:
            if len(tag) < 2 or len(tag) > 50:
                raise ValidationError("Tag must be between 2 and 50 characters")
            if not re.match(r"^[a-zA-Z0-9_\-]+$", tag):
                raise ValidationError(
                    "Tag can only contain letters, numbers, underscores and hyphens"
                )


class UpdatePostSchema(Schema):
    title = fields.String()
    description = fields.String()
    is_private = fields.Boolean()
    tags = fields.List(fields.String())

    @validates("title")
    def validate_title(self, value):
        if value and (len(value) < 3 or len(value) > 255):
            raise ValidationError("Title must be between 3 and 255 characters")

    @validates("description")
    def validate_description(self, value):
        if value and (len(value) < 10 or len(value) > 2000):
            raise ValidationError("Description must be between 10 and 2000 characters")

    @validates("tags")
    def validate_tags(self, value):
        if value:
            if len(value) > 10:
                raise ValidationError("Maximum 10 tags allowed")

            for tag in value:
                if len(tag) < 2 or len(tag) > 50:
                    raise ValidationError("Tag must be between 2 and 50 characters")
                if not re.match(r"^[a-zA-Z0-9_\-]+$", tag):
                    raise ValidationError(
                        "Tag can only contain letters, numbers, underscores and hyphens"
                    )


class ListPostsSchema(Schema):
    page = fields.Integer(default=1)
    per_page = fields.Integer(default=10)
    only_own = fields.Boolean(default=False)
    tags = fields.List(fields.String(), default=[])

    @validates("page")
    def validate_page(self, value):
        if value < 1:
            raise ValidationError("Page must be a positive integer")

    @validates("per_page")
    def validate_per_page(self, value):
        if value < 1 or value > 100:
            raise ValidationError("per_page must be between 1 and 100")
